from __future__ import annotations

import os
from typing import Any

import httpx

from .config import settings
from .knowledge_base import get_kb


class DataHubClient:
    """Клиент к DataHub для pull метаданных (ТЗ 1.2, v2).

    Получает:
    - dataset descriptions, column descriptions
    - owners, tags, glossary terms
    - lineage (происхождение данных)
    """

    def __init__(self, server_url: str = "", token: str = ""):
        self.server_url = (server_url or settings.datahub_url).rstrip("/")
        self.token = token or settings.datahub_token
        if not self.server_url:
            return

    @property
    def enabled(self) -> bool:
        return bool(self.server_url)

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _graphql(self, query: str, variables: dict | None = None) -> dict:
        """Выполнить GraphQL-запрос к DataHub."""
        payload = {"query": query, "variables": variables or {}}
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{self.server_url}/api/graphql",
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    def sync_datasets(self, limit: int = 100) -> dict:
        """Синхронизация описаний датасетов из DataHub в KB."""
        if not self.enabled:
            return {"error": "DataHub не настроен (datahub_url пуст)"}

        query = """
        query {
            datasets(input: {start: 0, count: %d}) {
                entities {
                    urn
                    name
                    description
                    platform { name }
                    schemaMetadata {
                        fields {
                            fieldPath
                            description
                            nativeDataType
                        }
                    }
                    ownership {
                        owners { owner { info { displayName } } }
                    }
                    glossaryTerms {
                        terms {
                            term {
                                info { name }
                            }
                        }
                    }
                    institutionalMemory {
                        elements {
                            url
                            description
                        }
                    }
                }
            }
        }
        """ % limit

        try:
            result = self._graphql(query)
        except Exception as e:
            return {"error": f"DataHub GraphQL: {e}"}

        entities = result.get("data", {}).get("datasets", {}).get("entities", [])
        kb = get_kb()
        synced = 0

        for entity in entities:
            name = entity.get("name", "")
            if not name:
                continue
            description = entity.get("description", "")
            platform = entity.get("platform", {}).get("name", "datahub")
            owners = entity.get("ownership", {})
            owner_name = ""
            if owners and owners.get("owners"):
                owner_name = owners["owners"][0].get("owner", {}).get("info", {}).get("displayName", "")

            tags = []
            glossary = entity.get("glossaryTerms", {})
            if glossary and glossary.get("terms"):
                tags = [t.get("term", {}).get("info", {}).get("name", "") for t in glossary["terms"]]
                tags = [t for t in tags if t]

            kb.upsert_table(
                table_name=name,
                connection=f"datahub:{platform}",
                description=description or None,
                owner=owner_name or None,
                tags=tags if tags else None,
                source="datahub",
            )

            # Колонки
            schema = entity.get("schemaMetadata", {})
            for field in schema.get("fields", []):
                field_path = field.get("fieldPath", "")
                field_desc = field.get("description", "")
                field_type = field.get("nativeDataType", "")
                if field_desc or field_type:
                    kb.upsert_column(
                        table_name=name,
                        column_name=field_path,
                        description=field_desc,
                        source="datahub",
                    )

            synced += 1

        kb_stats = {"synced": synced}
        return {"success": True, **kb_stats}

    def get_lineage(self, dataset_urn: str) -> dict:
        """Получить lineage для датасета (происхождение данных)."""
        if not self.enabled:
            return {"error": "DataHub не настроен"}

        query = """
        query($urn: String!) {
            lineage(urn: $urn) {
                upstreams {
                    degree
                    entity {
                        urn
                        name
                        type
                    }
                }
                downstreams {
                    degree
                    entity {
                        urn
                        name
                        type
                    }
                }
            }
        }
        """

        try:
            result = self._graphql(query, {"urn": dataset_urn})
            return result.get("data", {}).get("lineage", {})
        except Exception as e:
            return {"error": str(e)}
