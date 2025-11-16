multibranchPipelineJob('bsp-pipeline-main') {
  branchSources {
    branchSource {
      source {
        git {
          id('bsp-pipeline-main')
          remote('http://gitea:3000/bsp-dev/zcu102-bsp.git')
          credentialsId('gitea-admin-creds')
        }
      }
    }
  }
  factory {
    workflowBranchProjectFactory {
      scriptPath('Jenkinsfile')
    }
  }
}