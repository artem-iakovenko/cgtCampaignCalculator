from google.cloud import secretmanager


def access_secret(project_id: str, secret_id: str, version_id: str = "latest"):
  client = secretmanager.SecretManagerServiceClient()
  name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
  response = client.access_secret_version(request={"name": name})
  secret_value = response.payload.data.decode("UTF-8")
  return secret_value
