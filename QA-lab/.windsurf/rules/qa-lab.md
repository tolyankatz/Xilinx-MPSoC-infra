---
trigger: always_on
---

generation_rules:
  - if: "service needs persistent data"
    then: "define a named docker volume and map it in the service definition."
    example: "gitea_data for Gitea"
  - if: "service needs to communicate with another service"
    then: "ensure both services are on the shared_network."
  - if: "service is custom (not a pre-built image)"
    then: "create a build context directory containing a Dockerfile."