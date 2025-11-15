---
description: 
auto_execution_mode: 3
---

project_workflows:
  - name: "CI_Test_Run"
    description: "The end-to-end flow from code push to test execution."
    steps:
      - "Developer pushes code to Gitea."
      - "Jenkins polls Gitea and detects the change."
      - "Jenkins job starts."
      - "Jenkins job connects via SSH to the Host Controller service."
      - "Host Controller script executes."
      - "Host Controller connects to DUT Simulator's UART (TCP Port 23)."
      - "Host Controller runs network tests against DUT Simulator."
      - "Host Controller uploads results (logs) to MinIO service."
      - "Host Controller script finishes, returning status to Jenkins."