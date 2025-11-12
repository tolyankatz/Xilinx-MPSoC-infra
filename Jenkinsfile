// ===================================================================
// Jenkinsfile for ZCU102 BSP Hardware Validation Pipeline
// ===================================================================
// Triggered by new BSP artifacts in Artifactory
// Executes hardware validation on dedicated Test Host
// -------------------------------------------------------------------

pipeline {
    agent none
    
    // Trigger: Activated when new BSP artifacts are published
    triggers {
        artifactoryTrigger(
            spec: '''{
                "files": [
                    {
                        "pattern": "bsp-builds/**/*.yaml",
                        "buildName": "BSP-Validation-Pipeline"
                    },
                    {
                        "pattern": "bsp-dev-builds/**/*.yaml", 
                        "buildName": "BSP-Dev-Pipeline"
                    },
                    {
                        "pattern": "bsp-security/**/*.yaml",
                        "buildName": "BSP-Security-Pipeline"
                    }
                ]
            }'''
        )
    }
    
    // Parameters passed by Artifactory trigger or manual execution
    parameters {
        string(
            name: 'MANIFEST_PATH', 
            defaultValue: '', 
            description: 'Path to BSP manifest file in Artifactory'
        )
        string(
            name: 'BUILD_ID', 
            defaultValue: '', 
            description: 'Build identifier from manifest'
        )
        choice(
            name: 'TEST_SCOPE',
            choices: ['full', 'smoke', 'regression', 'security'],
            description: 'Test suite scope to execute'
        )
        booleanParam(
            name: 'FORCE_DEPLOYMENT',
            defaultValue: false,
            description: 'Force deployment even if validation fails'
        )
    }
    
    // Pipeline configuration
    options {
        timeout(time: 3, unit: 'HOURS')
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '30'))
        skipDefaultCheckout()
    }
    
    // Environment variables
    environment {
        // Test Host configuration
        TEST_HOST = credentials('test-host-endpoint')
        TEST_HOST_USER = credentials('test-host-user')
        
        // Notification endpoints
        SLACK_CHANNEL = '#bsp-validation'
        EMAIL_RECIPIENTS = 'bsp-team@company.com'
        
        // Artifact repository
        ARTIFACTORY_URL = 'https://artifactory.company.com/artifactory'
        
        // Framework paths on Test Host
        FRAMEWORK_PATH = '/opt/zcu102-bsp-validation'
        SCRIPTS_PATH = '/opt/zcu102-bsp-validation/scripts'
        MANIFESTS_PATH = '/opt/zcu102-bsp-validation/manifests'
    }
    
    stages {
        stage('1. Validation & Setup') {
            agent { label 'jenkins-controller' }
            steps {
                script {
                    echo "=== BSP Hardware Validation Pipeline Started ==="
                    echo "Manifest Path: ${params.MANIFEST_PATH}"
                    echo "Build ID: ${params.BUILD_ID}"
                    echo "Test Scope: ${params.TEST_SCOPE}"
                    echo "Force Deployment: ${params.FORCE_DEPLOYMENT}"
                    
                    // Validate required parameters
                    if (params.MANIFEST_PATH.isEmpty()) {
                        error "FATAL: MANIFEST_PATH parameter is required"
                    }
                    
                    // Extract build info from manifest path
                    env.MANIFEST_FILENAME = params.MANIFEST_PATH.split('/').last()
                    env.BUILD_TYPE = env.MANIFEST_FILENAME.contains('-dev-') ? 'development' :
                                    env.MANIFEST_FILENAME.contains('-hotfix-') ? 'hotfix' : 'stable'
                    
                    echo "Detected build type: ${env.BUILD_TYPE}"
                }
                
                // Archive pipeline parameters for reference
                writeFile file: 'pipeline-params.json', text: """
{
    "manifest_path": "${params.MANIFEST_PATH}",
    "build_id": "${params.BUILD_ID}",
    "test_scope": "${params.TEST_SCOPE}",
    "build_type": "${env.BUILD_TYPE}",
    "force_deployment": ${params.FORCE_DEPLOYMENT},
    "timestamp": "${env.BUILD_TIMESTAMP}",
    "job_name": "${env.JOB_NAME}",
    "build_number": "${env.BUILD_NUMBER}"
}
                """
                archiveArtifacts artifacts: 'pipeline-params.json'
            }
        }
        
        stage('2. Pre-Flight Checks') {
            agent { label 'jenkins-controller' }
            steps {
                script {
                    echo "=== Performing Pre-Flight Checks ==="
                    
                    // Check Test Host availability
                    sshagent(credentials: ['jenkins-test-host-key']) {
                        def hostCheck = sh(
                            script: """
                            ssh -o ConnectTimeout=30 -o StrictHostKeyChecking=no \
                            ${env.TEST_HOST_USER}@${env.TEST_HOST} \
                            'echo "Test Host accessible: \$(hostname) - \$(date)"'
                            """,
                            returnStdout: true
                        ).trim()
                        echo "Host Check Result: ${hostCheck}"
                    }
                    
                    // Verify framework availability on Test Host
                    sshagent(credentials: ['jenkins-test-host-key']) {
                        sh """
                        ssh ${env.TEST_HOST_USER}@${env.TEST_HOST} \
                        'test -d ${env.FRAMEWORK_PATH} && test -x ${env.SCRIPTS_PATH}/run_hw_tests.sh'
                        """
                    }
                    
                    echo "Pre-flight checks completed successfully"
                }
            }
        }
        
        stage('3. Hardware Validation Execution') {
            agent { label 'jenkins-controller' }
            steps {
                script {
                    echo "=== Starting Hardware Validation on Test Host ==="
                    
                    try {
                        sshagent(credentials: ['jenkins-test-host-key']) {
                            // Execute the validation framework
                            def testResult = sh(
                                script: """
                                ssh ${env.TEST_HOST_USER}@${env.TEST_HOST} \
                                '${env.SCRIPTS_PATH}/run_hw_tests.sh \
                                --manifest-path="${params.MANIFEST_PATH}" \
                                --build-id="${params.BUILD_ID}" \
                                --test-scope="${params.TEST_SCOPE}" \
                                --jenkins-build="${env.BUILD_NUMBER}" \
                                --force-deployment=${params.FORCE_DEPLOYMENT}'
                                """,
                                returnStatus: true
                            )
                            
                            // Store test result for post-processing
                            env.TEST_EXIT_CODE = testResult.toString()
                            
                            if (testResult != 0) {
                                echo "WARNING: Test execution returned non-zero exit code: ${testResult}"
                                if (!params.FORCE_DEPLOYMENT) {
                                    error "Hardware validation failed with exit code: ${testResult}"
                                }
                            }
                        }
                    } catch (Exception e) {
                        echo "ERROR during test execution: ${e.getMessage()}"
                        env.TEST_EXECUTION_ERROR = e.getMessage()
                        throw e
                    }
                }
            }
        }
        
        stage('4. Results Collection') {
            agent { label 'jenkins-controller' }
            steps {
                script {
                    echo "=== Collecting Test Results and Artifacts ==="
                    
                    sshagent(credentials: ['jenkins-test-host-key']) {
                        // Copy test results back to Jenkins
                        sh """
                        mkdir -p test-results logs screenshots
                        
                        # Copy test reports
                        scp -o StrictHostKeyChecking=no \
                        ${env.TEST_HOST_USER}@${env.TEST_HOST}:${env.FRAMEWORK_PATH}/test-results/* \
                        test-results/ || true
                        
                        # Copy execution logs  
                        scp -o StrictHostKeyChecking=no \
                        ${env.TEST_HOST_USER}@${env.TEST_HOST}:${env.FRAMEWORK_PATH}/logs/latest/* \
                        logs/ || true
                        
                        # Copy any screenshots from failures
                        scp -o StrictHostKeyChecking=no \
                        ${env.TEST_HOST_USER}@${env.TEST_HOST}:${env.FRAMEWORK_PATH}/screenshots/*.png \
                        screenshots/ || true
                        """
                    }
                    
                    // Archive all collected artifacts
                    archiveArtifacts artifacts: 'test-results/**, logs/**, screenshots/**', allowEmptyArchive: true
                    
                    // Publish test results if available
                    if (fileExists('test-results/junit.xml')) {
                        publishTestResults testResultsPattern: 'test-results/junit.xml'
                    }
                }
            }
        }
    }
    
    // Post-execution actions
    post {
        always {
            script {
                // Calculate execution duration
                def duration = currentBuild.duration ? "${currentBuild.duration / 1000}s" : "unknown"
                
                // Prepare summary message
                def status = currentBuild.result ?: 'SUCCESS'
                def summary = """
BSP Hardware Validation Pipeline Summary
=======================================
Status: ${status}
Build ID: ${params.BUILD_ID}
Test Scope: ${params.TEST_SCOPE}
Build Type: ${env.BUILD_TYPE ?: 'unknown'}
Duration: ${duration}
Test Host: ${env.TEST_HOST}
                """
                
                echo summary
            }
        }
        
        success {
            script {
                echo "=== PIPELINE SUCCESS ==="
                
                // Send success notification
                slackSend(
                    channel: env.SLACK_CHANNEL,
                    color: 'good',
                    message: """
:white_check_mark: BSP Validation PASSED
Build: ${params.BUILD_ID} (${env.BUILD_TYPE})
Test Scope: ${params.TEST_SCOPE}
Duration: ${currentBuild.duration / 1000}s
                    """
                )
                
                emailext(
                    to: env.EMAIL_RECIPIENTS,
                    subject: "BSP Validation SUCCESS: ${params.BUILD_ID}",
                    body: "Hardware validation completed successfully. See Jenkins build for details."
                )
            }
        }
        
        failure {
            script {
                echo "=== PIPELINE FAILURE ==="
                
                // Send failure notification with details
                slackSend(
                    channel: env.SLACK_CHANNEL,
                    color: 'danger',
                    message: """
:x: BSP Validation FAILED
Build: ${params.BUILD_ID} (${env.BUILD_TYPE})
Test Scope: ${params.TEST_SCOPE}
Error: ${env.TEST_EXECUTION_ERROR ?: 'See Jenkins logs'}
Jenkins: ${env.BUILD_URL}
                    """
                )
                
                emailext(
                    to: env.EMAIL_RECIPIENTS,
                    subject: "BSP Validation FAILURE: ${params.BUILD_ID}",
                    body: """
Hardware validation failed for build ${params.BUILD_ID}.
                    
Build Type: ${env.BUILD_TYPE}
Test Scope: ${params.TEST_SCOPE}
                    
Please check the Jenkins build logs for detailed information:
${env.BUILD_URL}
                    
Test execution error: ${env.TEST_EXECUTION_ERROR ?: 'See logs for details'}
                    """,
                    attachmentsPattern: 'logs/**, test-results/**'
                )
            }
        }
        
        unstable {
            script {
                slackSend(
                    channel: env.SLACK_CHANNEL,
                    color: 'warning', 
                    message: """
:warning: BSP Validation UNSTABLE
Build: ${params.BUILD_ID} (${env.BUILD_TYPE})
Some tests failed but deployment proceeded (force_deployment=true)
                    """
                )
            }
        }
    }
}
