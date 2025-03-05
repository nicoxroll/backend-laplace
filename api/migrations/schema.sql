Table users {
  id integer [primary key, increment]
  email varchar [not null, unique]
  username varchar [not null, unique]
  created_at timestamp [default: `CURRENT_TIMESTAMP`]
  updated_at timestamp [default: `CURRENT_TIMESTAMP`]
}

Table agents {
  id integer [primary key, increment]
  user_id integer [ref: > users.id, not null]
  name varchar [not null]
  is_private boolean [default: true, note: 'True=solo dueño puede ver']
  description text
  api_path varchar
  created_at timestamp [default: `CURRENT_TIMESTAMP`]
  updated_at timestamp [default: `CURRENT_TIMESTAMP`]
  
  indexes {
    (user_id, id) [unique]
  }
}

Table knowledge {
  id integer [primary key, increment]
  user_id integer [ref: > users.id, not null]
  name varchar [not null]
  vector_ids json [note: 'IDs en Weaviate']
  created_at timestamp [default: `CURRENT_TIMESTAMP`]
  updated_at timestamp [default: `CURRENT_TIMESTAMP`]
  
  indexes {
    (user_id, id) [unique]
  }
}

Table agent_knowledge {
  user_id integer [not null]
  agent_id integer [not null]
  knowledge_id integer [not null]
  created_at timestamp [default: `CURRENT_TIMESTAMP`]
  
  indexes {
    (user_id, agent_id, knowledge_id) [unique, pk]
  }
}

// Define the composite foreign keys outside the table definitions
Ref: agent_knowledge.(user_id, agent_id) > agents.(user_id, id)
Ref: agent_knowledge.(user_id, knowledge_id) > knowledge.(user_id, id)

Table analysis_results {
  id uuid [primary key]
  agent_id integer [ref: > agents.id]
  knowledge_ids json
  repo_ids json
  query varchar
  response varchar
  context_used json
  user_id integer [ref: > users.id]
  created_at timestamp [default: `CURRENT_TIMESTAMP`]
}

Table repositories {
  id integer [primary key, increment]
  user_id integer [ref: > users.id, not null]
  repo_url varchar [not null, unique]
  name varchar
  platform varchar [not null]
  last_indexed timestamp
  created_at timestamp [default: `CURRENT_TIMESTAMP`]
  updated_at timestamp [default: `CURRENT_TIMESTAMP`]
}

Table chats {
  id integer [primary key, increment]
  user_id integer [ref: > users.id, not null]
  agent_id integer [ref: > agents.id]
  title varchar
  created_at timestamp [default: `CURRENT_TIMESTAMP`]
  updated_at timestamp [default: `CURRENT_TIMESTAMP`]
}

Table user_settings {
  user_id integer [primary key, ref: > users.id]
  theme varchar [default: 'light']
  language varchar [default: 'en']
  created_at timestamp [default: `CURRENT_TIMESTAMP`]
  updated_at timestamp [default: `CURRENT_TIMESTAMP`]
}