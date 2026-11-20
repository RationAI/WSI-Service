import csv
import hashlib
import os
import pickle
import uuid

from fastapi import HTTPException
from filelock import FileLock
from pydantic_settings import BaseSettings, SettingsConfigDict

from wsi_service.base_mapper import BaseMapper
from wsi_service.models.local_mapper import CaseLocalMapper, SlideLocalMapper
from wsi_service.models.v3.storage import SlideStorage, StorageAddress
from wsi_service.singletons import logger
from wsi_service.utils.app_utils import local_mode_collect_secondary_files_v3


class CSVMapperSettings(BaseSettings):
    source: str = "data.csv"
    separator: str = "\t"
    group_1: int = 0
    group_2: int = 1
    slide_id: int = 2
    case_id: int = 3
    path: int = 4
    # Shape of the generated IDs. Placeholders: {group_1}, {group_2}, {slide_id}, {case_id},
    # {path} (the columns configured above) or {N} for any zero-based column index.
    # Use {{ and }} for literal braces.
    slide_id_template: str = "{group_1}.{group_2}.w.{slide_id}"
    case_id_template: str = "{group_1}.{group_2}.c.{case_id}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="csws_")


class IteratedCaseLocalMapper(CaseLocalMapper):
    group_1: str
    group_2: str
    context_id: str
    namespace: uuid.UUID
    to_import: bool


class IteratedSlideLocalMapper(SlideLocalMapper):
    group_1: str
    group_2: str
    context_id: str
    to_import: bool


NAMED_COLUMNS = ("group_1", "group_2", "slide_id", "case_id", "path")


class IdTemplate:
    """
    An ID template compiled against the configured column indexes, e.g.
    "{group_1}.{group_2}.w.{slide_id}" or "{0}-{7}". Deliberately not str.format:
    only column references are allowed, and the Rust port implements the same grammar.
    """

    def __init__(self, template, settings):
        columns = {name: getattr(settings, name) for name in NAMED_COLUMNS}
        self.parts = []  # str = literal text, int = column index
        literal = []
        i = 0
        while i < len(template):
            ch = template[i]
            if template.startswith("{{", i) or template.startswith("}}", i):
                literal.append(ch)
                i += 2
            elif ch == "{":
                end = template.find("}", i)
                if end == -1:
                    raise ValueError(f"ID template '{template}': unclosed '{{'")
                name = template[i + 1 : end].strip()
                if name.isascii() and name.isdigit():
                    column = int(name)
                elif name in columns:
                    column = columns[name]
                else:
                    raise ValueError(
                        f"ID template '{template}': unknown placeholder '{{{name}}}', "
                        f"expected a column index or one of {', '.join(NAMED_COLUMNS)}"
                    )
                if literal:
                    self.parts.append("".join(literal))
                    literal = []
                self.parts.append(column)
                i = end + 1
            elif ch == "}":
                raise ValueError(f"ID template '{template}': unmatched '}}' (use '}}}}' for a literal brace)")
            else:
                literal.append(ch)
                i += 1
        if literal:
            self.parts.append("".join(literal))
        self.columns = {part for part in self.parts if isinstance(part, int)}
        if not self.columns:
            raise ValueError(f"ID template '{template}' must reference at least one column")

    def render(self, row):
        return "".join(part if isinstance(part, str) else row[part] for part in self.parts)


def _column_or_empty(row, index):
    return row[index] if index < len(row) else ""


def create_case_object(settings, row, template, checked_groups):
    context_id = row[settings.case_id]
    group_1 = _column_or_empty(row, settings.group_1)
    group_2 = _column_or_empty(row, settings.group_2)

    # todo pydantic
    # only groups that end up in an ID are constrained
    for column in checked_groups:
        assert len(row[column]) <= 5

    namespace = uuid.uuid5(uuid.NAMESPACE_DNS, context_id)
    local_id = template.render(row)
    case = IteratedCaseLocalMapper(
        id=local_id,
        context_id=context_id,
        namespace=namespace,
        group_1=group_1,
        group_2=group_2,
        local_id=local_id,
        slides=[],
        to_import=True,
    )
    return case


def create_slide_object(settings, case, row, server_root, template):
    slide_local_id = row[settings.slide_id]

    local_id = template.render(row)
    addresses = local_mode_collect_secondary_files_v3(row[settings.path], local_id, local_id, server_root)
    slide = IteratedSlideLocalMapper(
        id=local_id,
        context_id=str(slide_local_id),
        local_id=local_id,
        case_local_id=case.local_id,
        group_1=case.group_1,
        group_2=case.group_2,
        to_import=True,
        slide_storage=SlideStorage(
            slide_id=local_id,
            storage_type="fs",
            storage_addresses=addresses,
        ),
    )
    return slide


class CSVMapper(BaseMapper):
    """
    CSV Mapper will read CSV file definitions: (indexes are configurable)
    GROUP_1       GROUP_2     SLIDE_ID     CASE        PATH
    <ID>          <VALUE>     <ID>         <CASE_ID>   <WSI-PATH>

    The slide ID will be created as such:   group_1.group_2.w.slide_id
    and mapped to the given path of the slide, which must be relative to the server root!
    All slides that belong to the same case must specify case id, which will be created as
    group_1.group_2.c.case_id (of the first group_1/group_2 found). All slides
    of a case should be within same group_2 and group_1.

    ID TEMPLATES:
    The shape of both IDs is configurable through CSWS_SLIDE_ID_TEMPLATE and
    CSWS_CASE_ID_TEMPLATE (defaults "{group_1}.{group_2}.w.{slide_id}" and
    "{group_1}.{group_2}.c.{case_id}"). A placeholder is either one of the configured
    columns - {group_1}, {group_2}, {slide_id}, {case_id}, {path} - or {N}, the zero-based
    index of any column in the file. {{ and }} give literal braces. The slide template must
    produce a unique value per row; IDs travel in URL paths, so avoid columns containing '/'.
    Group columns are only required (and limited to 5 characters) when a template uses them.
    Templates are not part of the cache key either: delete local_mapper.p after changing one.

    CACHING NOTE:
    Parsed data is cached to a pickle file (local_mapper.p). On startup the mapper only
    re-reads the CSV if the pickle is missing or the data_dir changed - the cache is NOT
    keyed on CSV content or mtime. This means editing the CSV (e.g. adding new file
    definitions) is NOT picked up by a plain restart: old entries keep working, new ones
    return 404. To pick up CSV changes, delete local_mapper.p (it will be rebuilt on next
    start) or trigger refresh(force_refresh=True).

    When running via Docker, a simple `docker restart` does NOT help - the pickle lives on
    the mounted volume and survives the restart. Delete local_mapper.p on the volume (or
    force a refresh) before restarting.
    """

    def __init__(self, data_dir):
        self.settings = CSVMapperSettings()
        # raises ValueError on a malformed template: fail at startup, not on first request
        self.slide_template = IdTemplate(self.settings.slide_id_template, self.settings)
        self.case_template = IdTemplate(self.settings.case_id_template, self.settings)
        used_columns = self.slide_template.columns | self.case_template.columns
        self.checked_groups = [
            column for column in (self.settings.group_1, self.settings.group_2) if column in used_columns
        ]
        super().__init__(data_dir)
        self.hash = None
        self.case_map = {}
        self.slide_map = {}
        self.refresh(force_refresh=False)

    def refresh(self, force_refresh=True):
        with FileLock("local_mapper.lock"):
            data_dir_changed = self._get_data_dir_changed()
            if force_refresh or data_dir_changed or not os.path.exists("local_mapper.p"):
                data = {}
                try:
                    self._read_csv_data()
                except Exception as e:
                    raise HTTPException(500, "Failed to parse the CSV file! Is your syntax correct?") from e

                data["data_dir"] = self.data_dir
                data["case_map"] = self.case_map
                data["slide_map"] = self.slide_map
                with open("local_mapper.p", "wb") as f:
                    pickle.dump(data, f)
        self.load()

    def load(self):
        updated_hash = self._get_updated_hash()
        if self.hash != updated_hash:
            with FileLock("local_mapper.lock"):
                with open("local_mapper.p", "rb") as f:
                    data = pickle.load(f)
                    self.case_map = data["case_map"]
                    self.slide_map = data["slide_map"]
                self.hash = self._get_updated_hash()

    def _read_csv_file(self, path):
        settings = self.settings
        case_map = {}
        slide_map = {}
        with open(path, "r") as file:
            reader = csv.reader(file, delimiter=settings.separator)
            for data in reader:
                case_id = data[settings.case_id]
                case = case_map.get(case_id, None)
                if case is None:
                    case = create_case_object(
                        settings=settings, row=data, template=self.case_template, checked_groups=self.checked_groups
                    )
                    case_map[case.id] = case
                slide = create_slide_object(
                    settings=settings,
                    case=case,
                    row=data,
                    server_root=self.data_dir,
                    template=self.slide_template,
                )
                case.slides.append(slide.id)
                slide_map[slide.id] = slide
        # successful: merge only now
        self.case_map.update(case_map)
        self.slide_map.update(slide_map)

    def _read_csv_data(self):
        self.case_map = {}
        self.slide_map = {}
        path = self.settings.source
        if os.path.isdir(path):
            found_data = False
            the_error = None
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith(".csv") or file.endswith(".tsv"):
                        try:
                            file_path = os.path.join(root, file)
                            self._read_csv_file(file_path)
                            found_data = True
                        except Exception as e:
                            the_error = e
            if not found_data and the_error is not None:
                logger.error(f"Directory {path} does not contain a valid data definition .tsv or .csv files!")
                raise HTTPException(status_code=500, detail=f"Invalid CSV source data!") from the_error
            elif not found_data:
                logger.info(f"Directory {path} does not contain any data.")

        elif os.path.isfile(path):
            try:
                self._read_csv_file(path)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Target CSV data definition is not a valid file!") from e

        else:
            logger.error(f"Path {path} is neither a file nor a directory.")
            raise HTTPException(status_code=500, detail=f"Invalid CSV source data!")

    def _get_updated_hash(self):
        return hashlib.md5(open("local_mapper.p", "rb").read()).hexdigest()

    def _get_data_dir_changed(self):
        data_dir_changed = False
        if os.path.exists("local_mapper.p"):
            with open("local_mapper.p", "rb") as f:
                data = pickle.load(f)
                data_dir_changed = data["data_dir"] != self.data_dir
        return data_dir_changed

    def get_cases(self, context=None):
        if context is not None:
            logger.warning(f"CSVMapper: received unexpected context='{context}', ignoring.")
        self.load()
        return list(self.case_map.values())

    def get_slides(self, case_id):
        self.load()
        if case_id not in self.case_map:
            raise HTTPException(status_code=404, detail=f"Case with case_id {case_id} does not exist")
        slide_data = []
        for slide_id in sorted(self.case_map[case_id].slides):
            slide_data.append(self.slide_map[slide_id])
        return slide_data

    def get_slide(self, slide_id):
        if slide_id not in self.slide_map:
            self.load()
            if slide_id not in self.slide_map:
                raise HTTPException(status_code=404, detail=f"Slide with slide_id {slide_id} does not exist")
        return self.slide_map[slide_id]
