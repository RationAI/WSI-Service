import re
import json
import traceback

from fastapi import HTTPException
from pydantic_settings import SettingsConfigDict

from ....rationai_receiver_auth.aaa_oauth import OAuthSettings, OAuthIntegration
from ....rationai_receiver_auth.lru_timeout_cache import LRUTimeoutCache
from wsi_service.models.v3.slide import SlideInfo

class WSAuthSettings(OAuthSettings):
    model_config = SettingsConfigDict(env_prefix="ws_", env_file=".env")


class LSAAIIntegration(OAuthIntegration):
    """
    LSAAI Resource Linking works the following way:
     - create a group, no child groups are allowed, name the group after the organization slug (up to 5 chars)
       - do not forget to add the user to the group :)
     - link the group to the target client/facility via resource
     - create attribute 'resource' with `res:[group]:[proj_slug]`

    For MMCI project Adopt we would create:
      - group mmci
      - link via resource named 'adopt'
      - attribute `res:mmci:adopt`
    """

    def __init__(self, settings, logger, http_client):
        super().__init__(settings, logger, WSAuthSettings(), {'Content-Type': 'application/json'})
        self._slide_cache = LRUTimeoutCache(self.auth_settings.user_cache_size, self.auth_settings.user_cache_timeout)

    def parse_user_info(self, data: str):
        user_info = json.loads(data)
        if "eduperson_entitlement" not in user_info:
            message = "User info does not contain eduperson_entitlement! Is the scope requested?"
            if "error" in user_info:
                message = user_info["error_description"] if "error_description" in user_info else user_info["error"]
            raise HTTPException(401, message)
        hierarchy = {}

        # Parse AARCG069 for groups
        for line in user_info["eduperson_entitlement"]:
            # parse group (institution) hierarchy
            match = re.search(r"^.*?:group:([^#\n]*)", line)
            if match:
                groups = match.group(1)
                # node = hierarchy
                if groups:
                    # Build group hierarchy
                    # for group in re.split(":", groups):
                    #     if not group in node:
                    #         node[group] = {}
                    #     node = node[group]

                    # For now we support just the leaf group -> flatten
                    group = re.split(":", groups)[-1]
                    hierarchy[group] = []
                continue
            # parse resource (project) that must be in form :res:inst:proj
            # todo what if we parse first res and then discover group? make sure the list is ordered or iterate twice
            match = re.search(r"^.*?:res:([^#\n:]+):([^#\n:]+)", line)
            if match:
                # For now we support just the leaf group -> flatten
                # group = self._find_user_group(match.group(1), hierarchy)
                group = hierarchy[match.group(1)]
                if type(group) == list and match.group(2) not in group:
                    group.append(match.group(2))
        return hierarchy

    # def _find_user_group(institution, node):
    #     for key in node:
    #         child = node[key]
    #         if child:
    #             if key == institution:
    #                 return child
    #             found = self._find_user_group(institution, child)
    #             if found:
    #                 return found
    #     return None

    def _resolve_proj_institution(self, institution, project, user_data):
        if not institution:
            return True
        if institution not in user_data:
            return False
        if not project:
            return True
        project_list = user_data[institution]
        return project in project_list

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
            if len(slide_id) == 3 and self._resolve_proj_institution(slide_id[0], None, user_data):
                return True
            # id without institution and project
            if len(slide_id) == 2:
                return True

        except Exception as e:
            traceback.print_exc()
            raise HTTPException(401, "Token or user info endpoint data is invalid!") from e

        raise HTTPException(403, f"Slide {slide_id} not available to the user!")
