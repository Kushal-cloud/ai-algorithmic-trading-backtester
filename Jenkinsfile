pipeline {
    agent any

    environment {
        REGISTRY = 'ghcr.io'
        IMAGE_NAME = 'kushal-cloud/ai-algorithmic-trading-backtester'
        IMAGE = "${REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER}"
        LATEST_IMAGE = "${REGISTRY}/${IMAGE_NAME}:latest"
        K8S_NAMESPACE = 'trading'
        K8S_DEPLOYMENT = 'trading-dashboard'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Test') {
            steps {
                sh '''
                    docker run --rm \
                      -v "$WORKSPACE:/app" \
                      -w /app \
                      python:3.11-slim \
                      bash -c "
                        pip install --no-cache-dir -r requirements.txt &&
                        pytest -q
                      "
                '''
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                    docker build \
                      -t "$IMAGE" \
                      -t "$LATEST_IMAGE" \
                      .
                '''
            }
        }

        stage('Docker Push') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'ghcr-credentials',
                    usernameVariable: 'REGISTRY_USER',
                    passwordVariable: 'REGISTRY_PASSWORD'
                )]) {
                    sh '''
                        echo "$REGISTRY_PASSWORD" | \
                          docker login "$REGISTRY" \
                          --username "$REGISTRY_USER" \
                          --password-stdin

                        docker push "$IMAGE"
                        docker push "$LATEST_IMAGE"

                        docker logout "$REGISTRY"
                    '''
                }
            }
        }

        stage('Deploy Kubernetes') {
            steps {
                sh '''
                    kubectl apply -f k8s/namespace.yaml
                    kubectl apply -f k8s/configmap.yaml
                    kubectl apply -f k8s/deployment.yaml
                    kubectl apply -f k8s/service.yaml
                    kubectl apply -f k8s/ingress.yaml

                    kubectl -n "$K8S_NAMESPACE" \
                      set image deployment/"$K8S_DEPLOYMENT" \
                      dashboard="$IMAGE"

                    kubectl -n "$K8S_NAMESPACE" \
                      rollout status deployment/"$K8S_DEPLOYMENT" \
                      --timeout=180s
                '''
            }
        }

        stage('Verify Deployment') {
            steps {
                sh '''
                    echo "=== Kubernetes Deployment ==="
                    kubectl -n "$K8S_NAMESPACE" \
                      get deployment "$K8S_DEPLOYMENT"

                    echo "=== Kubernetes Pods ==="
                    kubectl -n "$K8S_NAMESPACE" \
                      get pods -o wide

                    echo "=== Kubernetes Service ==="
                    kubectl -n "$K8S_NAMESPACE" \
                      get service

                    echo "=== Ingress ==="
                    kubectl -n "$K8S_NAMESPACE" \
                      get ingress
                '''
            }
        }
    }

    post {
        always {
            sh 'docker image prune -f || true'
        }

        success {
            echo "CI/CD pipeline completed successfully."
            echo "Image: ${IMAGE}"
        }

        failure {
            echo "CI/CD pipeline failed."
        }
    }
}
