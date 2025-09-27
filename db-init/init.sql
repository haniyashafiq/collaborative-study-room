CREATE USER studyuser WITH PASSWORD 'studypass';
CREATE DATABASE studyroom OWNER studyuser;
GRANT ALL PRIVILEGES ON DATABASE studyroom TO studyuser;