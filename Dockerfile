# syntax=docker/dockerfile:1
FROM nginx:alpine

# Copy the pre-built MkDocs site into nginx's default web root.
COPY site/ /usr/share/nginx/html/

# Health check and explicit signal handling are nginx defaults.
EXPOSE 80
