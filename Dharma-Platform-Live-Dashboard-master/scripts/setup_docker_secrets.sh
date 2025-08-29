#!/bin/bash
# Setup Docker secrets for production deployment

set -e

echo "🔐 Setting up Docker secrets for Dharma platform..."

# Check if running in Docker Swarm mode
if ! docker info | grep -q "Swarm: active"; then
    echo "❌ Docker Swarm is not active. Please initialize swarm mode first:"
    echo "   docker swarm init"
    exit 1
fi

# Function to create secret from environment variable
create_secret_from_env() {
    local secret_name=$1
    local env_var_name=$2
    local docker_secret_name="dharma_${secret_name}"
    
    if [ -z "${!env_var_name}" ]; then
        echo "❌ Environment variable $env_var_name is not set"
        return 1
    fi
    
    # Check if secret already exists
    if docker secret ls --format "{{.Name}}" | grep -q "^${docker_secret_name}$"; then
        echo "ℹ️  Secret $docker_secret_name already exists, removing..."
        docker secret rm "$docker_secret_name" || true
    fi
    
    # Create the secret
    echo "${!env_var_name}" | docker secret create "$docker_secret_name" -
    echo "✅ Created secret: $docker_secret_name"
}

# Function to create secret from file
create_secret_from_file() {
    local secret_name=$1
    local file_path=$2
    local docker_secret_name="dharma_${secret_name}"
    
    if [ ! -f "$file_path" ]; then
        echo "❌ File $file_path does not exist"
        return 1
    fi
    
    # Check if secret already exists
    if docker secret ls --format "{{.Name}}" | grep -q "^${docker_secret_name}$"; then
        echo "ℹ️  Secret $docker_secret_name already exists, removing..."
        docker secret rm "$docker_secret_name" || true
    fi
    
    # Create the secret
    docker secret create "$docker_secret_name" "$file_path"
    echo "✅ Created secret: $docker_secret_name"
}

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    echo "📄 Loading environment variables from .env file..."
    set -a
    source .env
    set +a
else
    echo "⚠️  No .env file found. Make sure environment variables are set."
fi

echo ""
echo "Creating API credential secrets..."

# Twitter API secrets
create_secret_from_env "twitter_api_key" "TWITTER_API_KEY"
create_secret_from_env "twitter_api_secret" "TWITTER_API_SECRET"
create_secret_from_env "twitter_bearer_token" "TWITTER_BEARER_TOKEN"
create_secret_from_env "twitter_access_token" "TWITTER_ACCESS_TOKEN"
create_secret_from_env "twitter_access_token_secret" "TWITTER_ACCESS_TOKEN_SECRET"

# YouTube API secrets
create_secret_from_env "youtube_api_key" "YOUTUBE_API_KEY"

# Telegram API secrets
create_secret_from_env "telegram_bot_token" "TELEGRAM_BOT_TOKEN"

# System secrets
create_secret_from_env "jwt_secret_key" "JWT_SECRET_KEY"
create_secret_from_env "encryption_key" "ENCRYPTION_KEY"

echo ""
echo "📋 Docker secrets created:"
docker secret ls --filter "name=dharma_" --format "table {{.Name}}\t{{.CreatedAt}}"

echo ""
echo "✅ Docker secrets setup completed!"
echo ""
echo "To deploy with secrets, use:"
echo "   docker stack deploy -c docker-compose.yml -c docker-compose.prod.yml -c docker-compose.secrets.yml dharma"
echo ""
echo "To remove all secrets:"
echo "   docker secret ls --filter 'name=dharma_' --format '{{.Name}}' | xargs docker secret rm"