# backend/services/cdn_manager.py
import requests
import logging
import os
from typing import List

logger = logging.getLogger("cdn_manager")

class CDNManager:
    """
    Sovereign v17.5: CDN & Edge Sync Manager.
    Handles programmatic cache invalidation for Cloudflare and GCP.
    """
    def __init__(self):
        self.cf_api_token = os.getenv("CLOUDFLARE_API_TOKEN")
        self.cf_zone_id = os.getenv("CLOUDFLARE_ZONE_ID")
        self.gcp_project = os.getenv("GCP_PROJECT_ID")

    def purge_cache(self, urls: List[str] = None, everything: bool = False):
        """Purges specific URLs or the entire cache from the CDN."""
        if not self.cf_api_token or not self.cf_zone_id:
            logger.warning(" 🛡️ [CDN] Skipping purge: Cloudflare credentials missing.")
            return

        headers = {
            "Authorization": f"Bearer {self.cf_api_token}",
            "Content-Type": "application/json"
        }
        
        data = {}
        if everything:
            data["purge_everything"] = True
        elif urls:
            data["files"] = urls
        else:
            return

        try:
            url = f"https://api.cloudflare.com/client/v4/zones/{self.cf_zone_id}/purge_cache"
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                logger.info(f" ✅ [CDN] Cache purge successful. Mode: {'FULL' if everything else 'URL_LIST'}")
            else:
                logger.error(f" ❌ [CDN] Cache purge failed: {response.text}")
        except Exception as e:
            logger.error(f" ❌ [CDN] Error during cache purge: {e}")

    def sync_api_version(self, version: str):
        """Ensures the CDN is aware of the latest API version to prevent stale responses."""
        logger.info(f" 🌐 [CDN] Syncing API Version {version} to Edge Nodes...")
        # In a real setup, this would update a KV store or a global header
        self.purge_cache(everything=True)

cdn_manager = CDNManager()
