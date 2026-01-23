# Guacamole Ansible Role

This role deploys Apache Guacamole on Ubuntu servers using Docker and Docker Compose.

## Requirements

- Ubuntu 22.04 (Jammy) or later
- Ansible 2.9+
- Python 3.6+
- Access to Docker Hub for pulling images

## Role Variables

### Required Variables

- `environment`: Environment name (dev, staging, production)
- `project_name`: Project name for resource naming
- `admin_email`: Administrator email address

### Optional Variables

- `guacamole_version`: Guacamole Docker image version (default: `latest`)
- `docker_compose_version`: Docker Compose version (default: `v2.24.0`)
- `guacamole_base_dir`: Base directory for Guacamole (default: `/opt/guacamole`)
- `guacamole_user`: User to run Guacamole services (default: `ubuntu`)
- `guacamole_admin_password`: Admin password (if set, auto-updates from default `guacadmin`)
- `domain_name`: Domain name for Let's Encrypt (default: `""`)
- `enable_lets_encrypt`: Enable Let's Encrypt SSL (default: `false`)
- `letsencrypt_email`: Email for Let's Encrypt notifications (default: `admin@<domain_name>`)

## Admin Password Management

The role can automatically update the Guacamole admin password from the default `guacadmin`:

```yaml
guacamole_admin_password: "your-secure-password"
```

**How it works:**

- If `guacamole_admin_password` is set to something other than `guacadmin`, the role will:
  1. Authenticate with the default credentials
  2. Update the password via the Guacamole REST API
  3. Verify the new password works
- If the default credentials fail (password already changed), the task is skipped
- This is idempotent - safe to run multiple times

**GitHub Actions:** Add secrets `GUACAMOLE_ADMIN_PASSWORD` (dev) and `PROD_GUACAMOLE_ADMIN_PASSWORD` (prod).

## Let's Encrypt SSL (Production)

When deploying to production with Let's Encrypt enabled:

1. **Prerequisites**:
   - DNS A record must point `domain_name` to the server's public IP
   - Port 80 must be accessible from the internet (for ACME challenge)
2. **How it works**:
   - Ansible automatically obtains the initial certificate using Certbot standalone mode
   - Certificates are stored in `{{ guacamole_base_dir }}/certbot/conf/`
   - A Certbot container runs continuously to auto-renew certificates every 12 hours
   - Nginx reloads every 6 hours to pick up renewed certificates

3. **Variables for production**:

   ```yaml
   enable_lets_encrypt: true
   domain_name: "guaclab.example.com"
   letsencrypt_email: "admin@example.com" # Optional, defaults to admin@<domain>
   ```

4. **Troubleshooting certificate issues**:

   ```bash
   # Check certificate status
   sudo docker run --rm -v /opt/guacamole/certbot/conf:/etc/letsencrypt certbot/certbot certificates

   # Force renewal
   sudo docker run --rm -v /opt/guacamole/certbot/conf:/etc/letsencrypt certbot/certbot renew --force-renewal
   ```

## Dependencies

- `community.docker` collection
- `community.general` collection
- `community.crypto` collection (for SSL certificate generation)

## Example Playbook

```yaml
- hosts: guacamole
  become: yes
  vars:
    environment: dev
    project_name: cyberlab
    admin_email: admin@example.com
    domain_name: guacamole.example.com
    enable_lets_encrypt: true
  roles:
    - guacamole
```

## What This Role Does

1. **System Setup**: Updates packages, installs prerequisites
2. **Docker Installation**: Installs Docker CE and Docker Compose
3. **Application Deployment**:
   - Generates secure database password
   - Initializes Guacamole database schema
   - Creates Docker Compose configuration
   - Sets up Nginx reverse proxy
   - Generates self-signed SSL certificate (if Let's Encrypt not enabled)
4. **CloudWatch Integration**: Installs and configures CloudWatch agent
5. **Management Scripts**: Creates helper scripts for status, restart, and logs

## Post-Deployment

After deployment, access Guacamole at:

- `https://<public-ip>/guacamole`
- Default credentials: `guacadmin` / `guacadmin` (CHANGE IMMEDIATELY)

Management commands:

- `guacamole-status`: Check service status
- `guacamole-restart`: Restart services
- `guacamole-logs [service]`: View logs

## License

MIT
