# User Stories for the CI/CD Lab Simulator

## As a BSP Developer...
- **I want to** easily create a new repository in Gitea for my feature branch.
- **I want to** see my Jenkins pipeline automatically start within one minute of pushing a code change.
- **I want to** have a direct link from the Jenkins build status back to my commit in Gitea, so I can quickly see what failed.

## As a QA Automation Engineer...
- **I want to** be able to SSH directly into the Host Controller container from my local machine to debug a failing test script.
- **I want to** easily download the full test logs for a failed build from the MinIO web interface.
- **I want to** have a pre-configured Jenkins job that I can manually trigger to run a specific test suite against a specific commit.