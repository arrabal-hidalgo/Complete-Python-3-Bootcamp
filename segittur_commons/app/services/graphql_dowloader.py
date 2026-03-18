from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

import httpx

# Standard GraphQL Introspection Query (shortened variant appropriate for schema download)
INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
    types {
      ...FullType
    }
    directives {
      name
      description
      locations
      args {
        ...InputValue
      }
    }
  }
}

fragment FullType on __Type {
  kind
  name
  description
  fields(includeDeprecated: true) {
    name
    description
    args {
      ...InputValue
    }
    type {
      ...TypeRef
    }
    isDeprecated
    deprecationReason
  }
  inputFields {
    ...InputValue
  }
  interfaces {
    ...TypeRef
  }
  enumValues(includeDeprecated: true) {
    name
    description
    isDeprecated
    deprecationReason
  }
  possibleTypes {
    ...TypeRef
  }
}

fragment InputValue on __InputValue {
  name
  description
  type { ...TypeRef }
  defaultValue
}

fragment TypeRef on __Type {
  kind
  name
  ofType {
    kind
    name
    ofType {
      kind
      name
      ofType {
        kind
        name
        ofType {
          kind
          name
        }
      }
    }
  }
}
"""

def download_graphql_schema(
        url: str,
        output_path: str = "schemas",
        output_file: str = "schema.json",
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
    ) -> str:
        """
        Download a GraphQL schema via the standard introspection query and save it to disk.

        Parameters:
            url: The GraphQL endpoint URL.
            output_path: Directory where the schema will be saved. Defaults to "schemas".
            output_file: File name for the saved schema (JSON). Defaults to "schema.json".
            headers: Optional HTTP headers to include in the request (e.g., authentication).
            timeout: Request timeout in seconds. Defaults to 30 seconds.

        Returns:
            The string path to the saved schema file.

        Raises:
            httpx.HTTPStatusError: If the HTTP request fails with a non-2xx status.
            ValueError: If the response does not contain a valid GraphQL introspection result.
        """
        if not url or not isinstance(url, str):
            raise ValueError("A valid GraphQL endpoint URL must be provided.")

        out_dir = Path(output_path).expanduser().resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / output_file

        payload = {"query": INTROSPECTION_QUERY}

        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        # Validate basic GraphQL introspection structure
        if not isinstance(data, dict):
            raise ValueError("Unexpected response format: expected JSON object.")

        if "errors" in data and data["errors"]:
            # Keep the full response for debugging but raise an exception
            raise ValueError(f"GraphQL returned errors: {data['errors']}")

        schema = data.get("data", {}).get("__schema")
        if schema is None:
            raise ValueError("Introspection result missing '__schema' field.")

        # Save the full introspection response for completeness
        with out_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return str(out_file)
