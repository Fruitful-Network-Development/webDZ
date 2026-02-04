# Email Service
I asked an old, previously confieded, chat session about this in regaruds to our prior conversation about an aws email set up, this is what is had to say:

You’re basically describing an email-control-plane data model: JSON that can describe what exists (domains, identities, inbound routes, outbound senders, newsletters), where it lives (region, ARNs, buckets), and how to operate it (which IAM role/secret to use), without encoding the orchestration logic.

Two important constraints before the schema:

Do not store long-lived credentials (AWS access keys, SMTP passwords) in JSON. Store references to a secrets system (AWS Secrets Manager / SSM Parameter Store / Vault) and keep the JSON declarative.

Model both:

resources (SES identities, rule sets, Lambda forwarders, S3 buckets, configuration sets)

bindings (receipt rule → actions, sender → configuration set, newsletter → audience)

Below is a practical schema you can implement directly.
1. Top-level structure
```json
{
  "schema_version": "1.0",
  "org_id": "fnd",
  "aws_accounts": [
    {
      "account_id": "065948377733",
      "alias": "primary",
      "default_region": "us-east-1",
      "assume_role": {
        "role_arn": "arn:aws:iam::065948377733:role/fnd-email-controlplane",
        "external_id_secret_ref": "secretsmanager://fnd/prod/controlplane/external_id"
      }
    }
  ],
  "domains": [],
  "identities": [],
  "inbound": [],
  "outbound": [],
  "newsletters": [],
  "observability": {}
}
```

2. Domain + DNS state (what exists and what must be true)
```json
{
  "domain": "fruitfulnetworkdevelopment.com",
  "account_ref": "primary",
  "region": "us-east-1",
  "dns": {
    "provider": "route53",
    "hosted_zone_id": "Z123EXAMPLE",
    "required_records": {
      "mx": [
        { "name": "@", "type": "MX", "value": "10 inbound-smtp.us-east-1.amazonaws.com" }
      ],
      "dkim_cname": [
        { "name": "abc._domainkey", "type": "CNAME", "value": "abc.dkim.amazonses.com" },
        { "name": "def._domainkey", "type": "CNAME", "value": "def.dkim.amazonses.com" },
        { "name": "ghi._domainkey", "type": "CNAME", "value": "ghi.dkim.amazonses.com" }
      ],
      "spf_txt": [
        { "name": "@", "type": "TXT", "value": "v=spf1 include:amazonses.com ~all" }
      ],
      "dmarc_txt": [
        { "name": "_dmarc", "type": "TXT", "value": "v=DMARC1; p=none; rua=mailto:dmarc@fruitfulnetworkdevelopment.com" }
      ]
    }
  },
  "ses_identity": {
    "identity_arn": "arn:aws:ses:us-east-1:065948377733:identity/fruitfulnetworkdevelopment.com",
    "verified": true,
    "dkim": { "enabled": true, "key_size": "rsa_2048" }
  }
}
```
And a sender mailbox identity if you ever need it:
```json
{
  "identity_id": "id_sender_dc",
  "type": "email",
  "value": "dcmontgomery@fruitfulnetworkdevelopment.com",
  "account_ref": "primary",
  "region": "us-east-1",
  "ses_identity_arn": "arn:aws:ses:us-east-1:065948377733:identity/dcmontgomery@fruitfulnetworkdevelopment.com",
  "verified": true
}
```
4. nbound “handlers” (receipt rules, S3, Lambda, routing):This is the core “relocation of inbound handlers” concept: you want a stable logical route that can be bound to different physical handlers.
```json
{
  "inbound_route_id": "inbound_fnd_default",
  "domain_ref": "fruitfulnetworkdevelopment.com",
  "match": {
    "rcpt": "@fruitfulnetworkdevelopment.com",
    "tls_policy": "optional",
    "spam_virus_scan": true
  },
  "ses_receiving": {
    "receipt_rule_set": {
      "name": "default-receive",
      "arn": "arn:aws:ses:us-east-1:065948377733:receipt-rule-set/default-receive"
    },
    "receipt_rule": {
      "name": "to-s3-then-lambda",
      "enabled": true,
      "actions": [
        {
          "type": "s3",
          "bucket": "ses-inbound-fnd-mail",
          "prefix": "inbox/",
          "kms_key_ref": null,
          "object_owner": "bucket-owner"
        },
        {
          "type": "lambda",
          "function_arn": "arn:aws:lambda:us-east-1:065948377733:function:ses-forwarder",
          "invocation": "event"
        }
      ]
    }
  },
  "handler_binding": {
    "active_handler_set_id": "handler_set_a",
    "handler_sets": [
      {
        "handler_set_id": "handler_set_a",
        "s3_bucket": "ses-inbound-fnd-mail",
        "lambda_function_arn": "arn:aws:lambda:us-east-1:065948377733:function:ses-forwarder"
      },
      {
        "handler_set_id": "handler_set_b",
        "s3_bucket": "ses-inbound-fnd-mail-alt",
        "lambda_function_arn": "arn:aws:lambda:us-east-1:065948377733:function:ses-forwarder-v2"
      }
    ]
  }
}
```
The handler_binding section is what makes “relocation” data-driven: you can flip active_handler_set_id without changing the conceptual route.

5. Outbound handlers (senders, configuration sets, feedback, API endpoints)
```json
{
  "outbound_handler_id": "out_fnd_primary",
  "account_ref": "primary",
  "region": "us-east-1",
  "sending": {
    "mode": "ses_api",
    "from_addresses": [
      { "address": "dcmontgomery@fruitfulnetworkdevelopment.com", "identity_ref": "id_fnd_domain" },
      { "address": "newsletter@fruitfulnetworkdevelopment.com", "identity_ref": "id_fnd_domain" }
    ],
    "configuration_set": {
      "name": "fnd-default",
      "event_destinations": [
        { "type": "cloudwatch", "namespace": "FND/Email" },
        { "type": "sns", "topic_arn": "arn:aws:sns:us-east-1:065948377733:fnd-ses-events" }
      ]
    }
  },
  "auth": {
    "iam_role_ref": "arn:aws:iam::065948377733:role/fnd-email-sender",
    "smtp": {
      "enabled": false,
      "smtp_endpoint": "email-smtp.us-east-1.amazonaws.com",
      "smtp_secret_ref": "secretsmanager://fnd/prod/ses/smtp_credentials"
    }
  },
  "suppression": {
    "global_suppression_list": true,
    "bounce_complaint_handling": "ses_managed"
  }
}
```
Notes:
mode: API vs SMTP
smtp_secret_ref: reference only (never inline secrets)

6. Newsletter objects (source references + audience + templates): You wanted “source references that notate an outbound newsletter.” Model it explicitly.
```json
{
  "newsletter_id": "nl_fnd_monthly",
  "name": "FND Monthly",
  "domain_ref": "fruitfulnetworkdevelopment.com",
  "outbound_handler_ref": "out_fnd_primary",
  "identity": {
    "from": "newsletter@fruitfulnetworkdevelopment.com",
    "reply_to": "dcmontgomery@fruitfulnetworkdevelopment.com"
  },
  "content_sources": [
    {
      "source_id": "src_blog_rss",
      "type": "rss",
      "uri": "https://fruitfulnetworkdevelopment.com/blog/rss.xml",
      "poll_interval": "PT6H"
    },
    {
      "source_id": "src_md_repo",
      "type": "git",
      "repo": "git@github.com:fruitfulnetworkdevelopment/fnd-content.git",
      "path": "newsletters/fnd-monthly/",
      "ref": "main"
    }
  ],
  "audience": {
    "list_provider": "internal",
    "list_ref": "db://platform.email_subscribers?list=fnd_monthly",
    "segments": [
      { "segment_id": "seg_ohio", "filter": { "state": "OH" } }
    ]
  },
  "delivery": {
    "schedule": { "type": "rrule", "value": "FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=1;BYHOUR=9;BYMINUTE=0" },
    "rate_limit_per_second": 1,
    "tracking": { "open_tracking": false, "click_tracking": false }
  },
  "compliance": {
    "list_unsubscribe": true,
    "footer_template_ref": "tpl_footer_can_spam",
    "physical_address_ref": "org_profile://fnd/postal_address"
  },
  "templates": {
    "html_template_ref": "ses-template://fnd-monthly-html",
    "text_template_ref": "ses-template://fnd-monthly-text"
  }
}
```
This cleanly separates:
identity (from/reply-to)
content sources
audience lists
schedule
compliance fields

7. Secrets and sensitive material (how to reference safely): Add a dedicated block so the JSON is explicit about where secrets live, without containing them:
```json
{
  "secrets": {
    "provider": "aws_secrets_manager",
    "refs": [
      {
        "name": "ses_smtp_credentials",
        "ref": "secretsmanager://fnd/prod/ses/smtp_credentials",
        "rotation": { "enabled": true, "interval_days": 60 }
      }
    ]
  }
}
```

8. Minimal “required fields” list (what you asked for)
If you strip it down to the essentials you said you care about (IDs, API endpoints, S3, addresses), the minimum set per environment is:
account_id
region
ses_identity_arn (domain)
receipt_rule_set name/arn
receipt_rule name + recipient match
s3_bucket (+ optional prefix)
lambda_function_arn
mx_target (inbound-smtp.<region>.amazonaws.com)
from_address(es)
forward_to destination (or forwarding map)
iam_role_arn for sender
secret_ref for SMTP/API if used