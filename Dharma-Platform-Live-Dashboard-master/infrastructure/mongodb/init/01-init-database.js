// MongoDB initialization script for Project Dharma

// Switch to the dharma_platform database
db = db.getSiblingDB('dharma_platform');

// Create application user
db.createUser({
  user: 'dharma_app',
  pwd: 'dharma_app_password',
  roles: [
    {
      role: 'readWrite',
      db: 'dharma_platform'
    }
  ]
});

// Create collections with validation schemas
db.createCollection('posts', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['platform', 'post_id', 'content', 'user_id', 'timestamp'],
      properties: {
        platform: {
          bsonType: 'string',
          enum: ['twitter', 'youtube', 'tiktok', 'telegram', 'web']
        },
        post_id: {
          bsonType: 'string'
        },
        content: {
          bsonType: 'string'
        },
        user_id: {
          bsonType: 'string'
        },
        timestamp: {
          bsonType: 'date'
        },
        metrics: {
          bsonType: 'object',
          properties: {
            likes: { bsonType: 'int' },
            shares: { bsonType: 'int' },
            comments: { bsonType: 'int' },
            views: { bsonType: 'int' }
          }
        },
        analysis_results: {
          bsonType: 'object',
          properties: {
            sentiment: {
              bsonType: 'string',
              enum: ['pro_india', 'neutral', 'anti_india']
            },
            confidence: {
              bsonType: 'double',
              minimum: 0,
              maximum: 1
            },
            bot_probability: {
              bsonType: 'double',
              minimum: 0,
              maximum: 1
            },
            risk_score: {
              bsonType: 'double',
              minimum: 0,
              maximum: 1
            }
          }
        }
      }
    }
  }
});

db.createCollection('campaigns', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['name', 'detection_date', 'status', 'coordination_score'],
      properties: {
        name: {
          bsonType: 'string'
        },
        detection_date: {
          bsonType: 'date'
        },
        status: {
          bsonType: 'string',
          enum: ['active', 'monitoring', 'resolved', 'false_positive']
        },
        coordination_score: {
          bsonType: 'double',
          minimum: 0,
          maximum: 1
        },
        participants: {
          bsonType: 'array',
          items: {
            bsonType: 'objectId'
          }
        }
      }
    }
  }
});

db.createCollection('user_profiles', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['platform', 'user_id', 'username'],
      properties: {
        platform: {
          bsonType: 'string',
          enum: ['twitter', 'youtube', 'tiktok', 'telegram']
        },
        user_id: {
          bsonType: 'string'
        },
        username: {
          bsonType: 'string'
        },
        behavioral_features: {
          bsonType: 'object'
        },
        bot_probability: {
          bsonType: 'double',
          minimum: 0,
          maximum: 1
        }
      }
    }
  }
});

// Create indexes for performance
// Posts collection indexes
db.posts.createIndex({ 'platform': 1, 'timestamp': -1 });
db.posts.createIndex({ 'user_id': 1, 'timestamp': -1 });
db.posts.createIndex({ 'analysis_results.sentiment': 1, 'timestamp': -1 });
db.posts.createIndex({ 'analysis_results.risk_score': -1 });
db.posts.createIndex({ 'content': 'text' }); // Text search index
db.posts.createIndex({ 'geolocation.coordinates': '2dsphere' }); // Geospatial index

// Campaigns collection indexes
db.campaigns.createIndex({ 'status': 1, 'detection_date': -1 });
db.campaigns.createIndex({ 'coordination_score': -1 });
db.campaigns.createIndex({ 'participants': 1 });

// User profiles collection indexes
db.user_profiles.createIndex({ 'platform': 1, 'user_id': 1 }, { unique: true });
db.user_profiles.createIndex({ 'bot_probability': -1 });
db.user_profiles.createIndex({ 'username': 1 });

print('MongoDB initialization completed successfully!');