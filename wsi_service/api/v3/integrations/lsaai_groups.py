import re
import json
import traceback

from fastapi import HTTPException
from pydantic_settings import SettingsConfigDict

from ....rationai_receiver_auth.aaa_oauth import OAuthSettings, OAuthIntegration
from ....rationai_receiver_auth.lru_timeout_cache import LRUTimeoutCache
from wsi_service.models.v3.slide import SlideInfo

class WSAuthSettings(OAuthSettings):
    # The prefix defines which rules are accepted, default rule accepts any urn:geant under any VO
    # The following restricts the selection to a common parent VO:
    #   urn:geant:lifescience-ri\.eu:group:ration_ai
    # Note that the prefix must remove any characters such that we receive the following group
    # as the first one - the PROJECT
    lsaai_regex_prefix: str = ".*?:group:[^:]+"
    model_config = SettingsConfigDict(env_prefix="ws_", env_file=".env")


class LSAAIIntegration(OAuthIntegration):
    """
    LSAAI Group Linking works the following way:
     - there are three levels of groups:
       1) project - must be the top level group parsed, e.g. if you leave default lsaai_regex_prefix,
          then if VO is the parent 'group' to all groups, it will treat VO as project -> you can remove
          the VO 'vo' by using e.g. ".*?:group:vo:[^:]+"
       2) institution - institution as a subgroup of project if it contributes with data
       3) access rights (write for now only, read access = membership)
    """

    def __init__(self, settings, logger, http_client):
        super().__init__(settings, logger, WSAuthSettings(), {'Content-Type': 'application/json'})
        self._slide_cache = LRUTimeoutCache(self.auth_settings.user_cache_size, self.auth_settings.user_cache_timeout)

    def _ensure_child_exists(self, node, key):
        child = node.get(key, None)
        if child is None:
            child = {}
            node[key] = child
        return child

    def parse_user_info(self, data: str):
        user_info = json.loads(data)
        hierarchy = {}

        if "eduperson_entitlement" not in user_info:
            if "error" in user_info:
                message = user_info["error_description"] if "error_description" in user_info else user_info["error"]
                raise HTTPException(401, message)
            return hierarchy
        # Parse AARCG069 for groups

        for line in user_info["eduperson_entitlement"]:
            # parse group (institution) hierarchy
            match = re.search(fr"^{self.auth_settings.lsaai_regex_prefix}:?([^#\n]*)", line)
            if match:
                groups = match.group(1)
                # node = hierarchy
                if groups:
                    group_list = re.split(":", groups)
                    length = len(group_list)
                    project = group_list[0]
                    institution = group_list[1] if length > 1 else ""
                    rights = group_list[2] if length > 2 else None

                    proj_node = self._ensure_child_exists(hierarchy, project)
                    inst_node = self._ensure_child_exists(proj_node, institution)
                    if rights is not None:
                        inst_node["rights"] = [rights]
                continue

        return hierarchy

    def _resolve_proj_institution(self, institution, project, user_data):
        project_data = user_data.get(project, None)
        institution_data = project_data.get(institution, None) if project_data is not None else None
        return (
            institution == "" or institution_data is not None
        ) and (
            project == "" or project_data is not None
        )


    async def allow_access_slide(self, auth_payload, slide_id, manager, plugin, slide=None):
        try:
            if isinstance(slide, SlideInfo):
                self._slide_cache.put_item(slide_id, slide)
            else:
                slide = self._slide_cache.get_item(slide_id)
                if not slide:
                    slide = await manager.get_slide_info(slide_id, slide_info_model=SlideInfo, plugin=plugin)
                    self._slide_cache.put_item(slide_id, slide)

            user_data = await self.get_user_info(auth_payload)
            slide_id = re.split("\.", slide.id)
            # possibly project and institution
            if len(slide_id) == 4 and self._resolve_proj_institution(slide_id[0], slide_id[1], user_data):
                return True
            # id without project
            if len(slide_id) == 3 and self._resolve_proj_institution(slide_id[0], "", user_data):
                return True
            # id without institution and project
            if len(slide_id) == 2:
                return True

        except Exception as e:
            traceback.print_exc()
            raise HTTPException(401, "Token or user info endpoint data is invalid!") from e

        raise HTTPException(403, f"Slide {slide_id} not available to the user!")
