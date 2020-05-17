#!groovy

def PYTHON_VERSION = '3.8'
pipeline {
  options {
    buildDiscarder logRotator(artifactDaysToKeepStr: '', artifactNumToKeepStr: '3', daysToKeepStr: '', numToKeepStr: '')
    gitLabConnection('gitlab@cr.imson.co')
    gitlabBuilds(builds: ['jenkins'])
    disableConcurrentBuilds()
    timestamps()
  }
  post {
    failure {
      updateGitlabCommitStatus name: 'jenkins', state: 'failed'
    }
    unstable {
      updateGitlabCommitStatus name: 'jenkins', state: 'failed'
    }
    aborted {
      updateGitlabCommitStatus name: 'jenkins', state: 'canceled'
    }
    success {
      updateGitlabCommitStatus name: 'jenkins', state: 'success'
    }
    always {
      cleanWs()
    }
  }
  agent {
    docker {
      image "docker.cr.imson.co/python-lambda-layer-builder:${PYTHON_VERSION}"
    }
  }
  environment {
    CI = 'true'
    AWS_REGION = 'us-east-2'
  }
  stages {
    stage('Prepare') {
      steps {
        updateGitlabCommitStatus name: 'jenkins', state: 'running'
        sh 'python --version && pip --version'
      }
    }

    stage('QA') {
      environment {
        HOME = "${env.WORKSPACE}"
      }
      steps {
        sh "pip install --user --no-cache --progress-bar off -r ${env.WORKSPACE}/deps/boto3layer/requirements.txt"
        sh "pip install --user --no-cache --progress-bar off -r ${env.WORKSPACE}/deps/xraylayer/requirements.txt"
        sh "pip install --user --no-cache --progress-bar off -e ${env.WORKSPACE}/deps/crimsoncore/lib/"

        sh "find ${env.WORKSPACE}/src -type f -iname '*.py' -print0 | xargs -0 python -m pylint"
      }
    }

    stage('Deploy lambda') {
      when {
        branch 'master'
      }
      steps {
        sh "mkdir -p ${env.WORKSPACE}/build/"
        sh "cp ${env.WORKSPACE}/src/*.py ${env.WORKSPACE}/build/"

        dir("${env.WORKSPACE}/build/") {
          sh "zip -r lambda.zip *"
        }

        archiveArtifacts 'build/lambda.zip'

        withCredentials([file(credentialsId: '69902ef6-1a24-4740-81fa-7b856248987d', variable: 'AWS_SHARED_CREDENTIALS_FILE')]) {
          withCredentials([string(credentialsId: 'c51c8b4c-ea81-453f-bc5b-d44cd5b00175', variable: 'SCHEDULED_ON_LAMBDA_ARN')]) {
            sh """
              aws lambda update-function-code \
                --region ${env.AWS_REGION} \
                --function-name "${env.SCHEDULED_ON_LAMBDA_ARN}" \
                --zip-file fileb://./build/lambda.zip \
                --publish
            """.stripIndent()
          }
        }
      }
    }
  }
}
