pipeline {

   agent any

   environment {

       APP_SERVER = '3.142.140.253'

       RELEASE = "uta-attendance-${BUILD_NUMBER}.tar.gz"

   }

   stages {

       stage('Checkout') {


    steps { checkout scm; sh 'git log -1 --oneline' }

}

stage('Build Environment') {

    steps {

        sh '''

          rm -rf .venv

          python3 -m venv .venv

          .venv/bin/pip install --upgrade pip

          .venv/bin/pip install -r requirements.txt

        '''

    }

}

stage('Lint') {

    steps { sh '.venv/bin/flake8 app.py tests --max-line-length=120' }

}

stage('Test') {

    steps { sh '.venv/bin/pytest -q --junitxml=test-results.xml' }

    post { always { junit 'test-results.xml' } }

}

stage('Package') {

    steps {

        sh '''

          rm -rf release

          mkdir release

          cp -r app.py requirements.txt templates static release/

          tar -czf ${RELEASE} -C release .

        '''

        archiveArtifacts artifacts: '*.tar.gz', fingerprint: true

    }

}

stage('Deploy') {

    steps {

        sshagent(credentials: ['uta-app-ssh']) {

          sh '''


                          scp -o StrictHostKeyChecking=no ${RELEASE} deployer@${APP_SERVER}:/tmp/${RELEASE}

                          ssh -o StrictHostKeyChecking=no deployer@${APP_SERVER} \

                              "sudo /usr/local/sbin/deploy-uta-attendance ${BUILD_NUMBER} /tmp/${RELEASE}"

                        '''

                    }

                }

            }

            stage('Verify') {

                steps { sh 'sleep 3; curl --fail http://${APP_SERVER}/health' }

            }

        }

        post {

            success { echo "Deployment ${BUILD_NUMBER} completed successfully." }

            failure { echo 'Pipeline failed. Review the failed stage and console log.' }

        }

    }
