@Library('juju-pipeline@master') _

pipeline {
    agent {
        label "${params.build_node}"
    }
    /* XXX: Global $PATH setting doesn't translate properly in pipelines
     https://stackoverflow.com/questions/43987005/jenkins-does-not-recognize-command-sh
     */
    environment {
        PATH = "${utils.cipaths}"
        GITHUB_CREDS = credentials('cdkbot_github')
    }
    options {
        ansiColor('xterm')
        timestamps()
    }
    stages {
        stage('Setup') {
            steps {
                sh "snapcraft login --with /var/lib/jenkins/snapcraft-creds"
            }
        }
        stage('Promote Snaps'){
            steps {
                sh "SNAPS=${params.snaps} PROMOTE_FROM='${params.promote_from}' PROMOTE_TO='${params.promote_to}' KUBE_ARCH='${params.arch}' GH_USER='${env.GITHUB_CREDS_USR}' GH_TOKEN='${env.GITHUB_CREDS_PSW}' bash jobs/build-snaps/promote.sh"
            }
        }
    }
    post {
        always {
            sh "sudo rm -rf release/snap"
            sh "snapcraft logout"
        }
    }
}
