FROM postgres:15-alpine

# Install extensions for better performance and functionality
RUN apk add --no-cache postgresql-contrib

# Set environment variables
ENV POSTGRES_DB=gst_service_center
ENV POSTGRES_USER=gst_user
ENV POSTGRES_PASSWORD=gst_password_2023

# Copy initialization scripts
COPY init.sql /docker-entrypoint-initdb.d/

# Expose port
EXPOSE 5432

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pg_isready -U $POSTGRES_USER -d $POSTGRES_DB