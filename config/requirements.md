# Organization requirements (Fieldline Run Club)

- Static website with at least five linked pages and the same navigation on every page.
- At least one client-side JavaScript feature and a custom 404 error page.
- Files stored in a private S3 bucket and delivered only through CloudFront.
- Served on csce412prra2413.me over HTTPS with a valid certificate; HTTP must redirect to HTTPS.
- Direct anonymous access to the S3 objects must be denied.
- Deployments must be repeatable, and every deployment must be verified.
- Changes to security settings (bucket policy, CloudFront, DNS) need human approval.
