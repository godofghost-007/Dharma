#!/bin/bash

# Initialize Elasticsearch indices for Project Dharma

set -e

ELASTICSEARCH_URL=${ELASTICSEARCH_URL:-"http://localhost:9200"}
MAPPING_DIR="./mappings"

echo "Initializing Elasticsearch indices..."

# Wait for Elasticsearch to be ready
echo "Waiting for Elasticsearch to be ready..."
until curl -s "$ELASTICSEARCH_URL/_cluster/health" > /dev/null; do
    echo "Waiting for Elasticsearch..."
    sleep 5
done

echo "Elasticsearch is ready!"

# Create posts index
echo "Creating posts index..."
curl -X PUT "$ELASTICSEARCH_URL/dharma-posts" \
  -H "Content-Type: application/json" \
  -d @"$MAPPING_DIR/posts-mapping.json"

# Create campaigns index
echo "Creating campaigns index..."
curl -X PUT "$ELASTICSEARCH_URL/dharma-campaigns" \
  -H "Content-Type: application/json" \
  -d @"$MAPPING_DIR/campaigns-mapping.json"

# Create index templates for time-based indices
echo "Creating index template for daily posts..."
curl -X PUT "$ELASTICSEARCH_URL/_index_template/dharma-posts-daily" \
  -H "Content-Type: application/json" \
  -d '{
    "index_patterns": ["dharma-posts-*"],
    "template": {
      "settings": {
        "number_of_shards": 2,
        "number_of_replicas": 1,
        "index.lifecycle.name": "dharma-posts-policy",
        "index.lifecycle.rollover_alias": "dharma-posts"
      },
      "mappings": {
        "properties": {
          "timestamp": {
            "type": "date",
            "format": "strict_date_optional_time||epoch_millis"
          }
        }
      }
    }
  }'

# Create ILM policy for log rotation
echo "Creating ILM policy..."
curl -X PUT "$ELASTICSEARCH_URL/_ilm/policy/dharma-posts-policy" \
  -H "Content-Type: application/json" \
  -d '{
    "policy": {
      "phases": {
        "hot": {
          "actions": {
            "rollover": {
              "max_size": "10GB",
              "max_age": "7d"
            }
          }
        },
        "warm": {
          "min_age": "7d",
          "actions": {
            "allocate": {
              "number_of_replicas": 0
            }
          }
        },
        "cold": {
          "min_age": "30d",
          "actions": {
            "allocate": {
              "number_of_replicas": 0
            }
          }
        },
        "delete": {
          "min_age": "90d"
        }
      }
    }
  }'

echo "Elasticsearch indices initialized successfully!"