// ============================================================================
// ACEest Fitness & Gym - CI/CD Pipeline
// ============================================================================
// Stages:
//   1. Checkout         - pull source from GitHub
//   2. Setup            - create virtualenv & install deps
//   3. Lint             - flake8 sanity check
//   4. Unit Test        - pytest with coverage (fails build on regression)
//   5. SonarQube        - static analysis + quality gate
//   6. Build Image      - docker build with version + git SHA tags
//   7. Image Scan       - trivy CVE scan
//   8. Push Image       - docker push to Docker Hub
//   9. Deploy           - kubectl apply for the chosen strategy
//  10. Smoke Test       - hit /health on the deployed Service
//  11. Promote / Rollback
// ============================================================================

pipeline {
  agent any

  options {
    timestamps()
    timeout(time: 30, unit: 'MINUTES')
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  parameters {
    choice(name: 'DEPLOY_STRATEGY',
           choices: ['rolling-update', 'blue-green', 'canary', 'ab-testing', 'shadow', 'none'],
           description: 'Which Kubernetes deployment strategy to apply')
    booleanParam(name: 'RUN_SONAR', defaultValue: true,
                 description: 'Run SonarQube analysis & quality gate')
    booleanParam(name: 'PUSH_IMAGE', defaultValue: true,
                 description: 'Push the built image to Docker Hub')
  }

  environment {
    APP_NAME       = 'aceest-fitness'
    DOCKER_REGISTRY= 'docker.io'
    DOCKER_NS      = 'youraccount'                 // <-- replace with your Docker Hub user
    IMAGE          = "${DOCKER_NS}/${APP_NAME}"
    APP_VERSION    = '3.2.4'                       // bumped per release branch
    K8S_NAMESPACE  = 'aceest'
    SONAR_PROJECT  = 'aceest-fitness'
    PYTHON         = 'python3'
  }

  stages {

    stage('Checkout') {
      steps {
        checkout scm
        script {
          env.GIT_SHA = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
          env.IMAGE_TAG = "${env.APP_VERSION}-${env.GIT_SHA}-${env.BUILD_NUMBER}"
          echo "Build tag: ${env.IMAGE_TAG}"
        }
      }
    }

    stage('Setup') {
      steps {
        sh '''
          set -eux
          ${PYTHON} -m venv .venv
          . .venv/bin/activate
          pip install --upgrade pip
          pip install -r requirements-dev.txt
          pip install flake8
        '''
      }
    }

    stage('Lint') {
      steps {
        sh '''
          set -eux
          . .venv/bin/activate
          flake8 app/ tests/ --max-line-length=110 --statistics
        '''
      }
    }

    stage('Unit Test') {
      steps {
        sh '''
          set -eux
          . .venv/bin/activate
          pytest tests/ \
            --junitxml=test-results.xml \
            --cov=app --cov-report=xml:coverage.xml --cov-report=term \
            -v
        '''
      }
      post {
        always {
          junit 'test-results.xml'
          archiveArtifacts artifacts: 'coverage.xml,test-results.xml',
                           allowEmptyArchive: true
        }
      }
    }

    stage('SonarQube Analysis') {
      when { expression { return params.RUN_SONAR } }
      steps {
        withSonarQubeEnv('SonarQubeServer') {
          sh '''
            set -eux
            sonar-scanner \
              -Dsonar.projectKey=${SONAR_PROJECT} \
              -Dsonar.sources=app \
              -Dsonar.tests=tests \
              -Dsonar.python.coverage.reportPaths=coverage.xml \
              -Dsonar.python.xunit.reportPath=test-results.xml
          '''
        }
        timeout(time: 5, unit: 'MINUTES') {
          waitForQualityGate abortPipeline: true
        }
      }
    }

    stage('Build Image') {
      steps {
        sh '''
          set -eux
          docker build \
            --build-arg APP_VERSION=${APP_VERSION} \
            --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
            --build-arg VCS_REF=${GIT_SHA} \
            -t ${IMAGE}:${IMAGE_TAG} \
            -t ${IMAGE}:${APP_VERSION} \
            -t ${IMAGE}:latest \
            .
        '''
      }
    }

    stage('Image Scan (Trivy)') {
      steps {
        sh '''
          set -eu
          if command -v trivy >/dev/null; then
            trivy image --exit-code 0 --severity HIGH,CRITICAL --no-progress ${IMAGE}:${IMAGE_TAG}
          else
            echo "Trivy not installed on agent - skipping scan."
          fi
        '''
      }
    }

    stage('Push Image') {
      when { expression { return params.PUSH_IMAGE } }
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                                          usernameVariable: 'DOCKER_USER',
                                          passwordVariable: 'DOCKER_PASS')]) {
          sh '''
            set -eu
            echo "$DOCKER_PASS" | docker login ${DOCKER_REGISTRY} -u "$DOCKER_USER" --password-stdin
            docker push ${IMAGE}:${IMAGE_TAG}
            docker push ${IMAGE}:${APP_VERSION}
            docker push ${IMAGE}:latest
            docker logout ${DOCKER_REGISTRY}
          '''
        }
      }
    }

    stage('Deploy to Kubernetes') {
      when { expression { return params.DEPLOY_STRATEGY != 'none' } }
      steps {
        withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
          sh '''
            set -eux
            kubectl --kubeconfig=$KUBECONFIG apply -f k8s/base/namespace.yaml
            # Render image tag into manifests
            mkdir -p .rendered
            for f in k8s/${DEPLOY_STRATEGY}/*.yaml; do
              sed "s|IMAGE_PLACEHOLDER|${IMAGE}:${IMAGE_TAG}|g" "$f" > ".rendered/$(basename $f)"
            done
            kubectl --kubeconfig=$KUBECONFIG -n ${K8S_NAMESPACE} apply -f .rendered/
            kubectl --kubeconfig=$KUBECONFIG -n ${K8S_NAMESPACE} rollout status \
              deployment/${APP_NAME} --timeout=120s || \
            kubectl --kubeconfig=$KUBECONFIG -n ${K8S_NAMESPACE} get all
          '''
        }
      }
    }

    stage('Smoke Test') {
      when { expression { return params.DEPLOY_STRATEGY != 'none' } }
      steps {
        withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
          sh '''
            set -eu
            URL=$(kubectl --kubeconfig=$KUBECONFIG -n ${K8S_NAMESPACE} get svc ${APP_NAME} \
                  -o jsonpath='{.status.loadBalancer.ingress[0].ip}' || true)
            if [ -z "$URL" ]; then
              # Minikube fallback
              URL=$(minikube service ${APP_NAME} -n ${K8S_NAMESPACE} --url || echo "")
            fi
            echo "Probing $URL/health"
            for i in 1 2 3 4 5; do
              if curl -fsS "${URL}/health"; then echo " - healthy"; exit 0; fi
              sleep 5
            done
            echo "Smoke test failed"; exit 1
          '''
        }
      }
    }
  }

  post {
    success {
      echo "Build ${env.BUILD_NUMBER} succeeded - image ${env.IMAGE}:${env.IMAGE_TAG} deployed via ${params.DEPLOY_STRATEGY}"
    }
    failure {
      echo "Build failed - rolling back the last successful deployment"
      withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
        sh '''
          set -eu
          kubectl --kubeconfig=$KUBECONFIG -n ${K8S_NAMESPACE} rollout undo \
            deployment/${APP_NAME} || true
        '''
      }
    }
    always {
      sh 'docker image prune -f || true'
      cleanWs()
    }
  }
}
