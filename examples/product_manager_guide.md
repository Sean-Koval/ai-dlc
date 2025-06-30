# Product Manager's Guide: Generating a Voice Analytics Template

As a Product Manager for AI-enabled products, one of our key tasks is to analyze customer interactions to identify pain points and feature opportunities. This guide will walk you through using the `generate-template` command to create a Jinja2 template for summarizing voice analytics transcripts.

## 1. The Use Case

We want to create a standardized summary for each customer call transcript. This summary should highlight key information like sentiment, identified topics, and a brief overview of the conversation. This will help us quickly triage customer feedback and identify trends.

## 2. The Schema

First, we need a schema that represents the data we get from our voice analytics service. We've defined this in `examples/voice_analytics_schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Voice Analytics Transcript",
  "type": "object",
  "properties": {
    "transcript_id": {
      "type": "string"
    },
    "customer_id": {
      "type": "string"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "sentiment": {
      "type": "string",
      "enum": ["positive", "neutral", "negative"]
    },
    "key_topics": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "full_transcript": {
      "type": "string"
    }
  },
  "required": ["transcript_id", "full_transcript"]
}
```

## 3. Generating the Template

Now, we'll use the `generate-template` command. We'll specify our role, the task, and the path to our schema. We'll also provide some directives to guide the LLM in creating the template.

```bash
ai-dlc generate-template \
  --role "As a Product Manager for AI-enabled products" \
  --task "I need to create a summary of a voice analytics transcript to quickly identify customer pain points and feature opportunities." \
  --directives "Create a summary with sections for sentiment, key topics, and a brief overview of the conversation." \
  --schema examples/voice_analytics_schema.json \
  --output-file examples/generated_template.md
```

## 4. The Generated Template

Here is the output from the command, saved to `examples/generated_template.md`:

```jinja
# Voice Analytics Transcript Summary

**Transcript ID:** {{ transcript_id }}
**Customer ID:** {{ customer_id }}
**Timestamp:** {{ timestamp }}

## Sentiment Analysis

{% if sentiment == 'positive' %}
- **Sentiment:** Positive 😊
{% elif sentiment == 'neutral' %}
- **Sentiment:** Neutral 😐
{% elif sentiment == 'negative' %}
- **Sentiment:** Negative 😠
{% else %}
- **Sentiment:** Not Analyzed
{% endif %}

## Key Topics Discussed

<ul>
{% for topic in key_topics %}
  <li>{{ topic }}</li>
{% endfor %}
</ul>

## Conversation Overview

> {{ full_transcript | truncate(200) }}

---

### VALIDATION:
- **transcript_id**: {{ transcript_id is defined and transcript_id is not none }}
- **sentiment**: {{ sentiment in ['positive', 'neutral', 'negative'] }}
- **key_topics**: {{ key_topics is iterable and key_topics is not string }}
```

## 5. Evaluation and How to Use It

The generated template is a great starting point. Here's how it helps:

*   **Standardization:** It provides a consistent format for all our call summaries, making it easier to compare and analyze them.
*   **At-a-Glance Insights:** The sentiment and key topics sections allow us to quickly understand the gist of the conversation without reading the full transcript.
*   **Data-Driven:** The template is directly tied to our schema, ensuring that we're always using the correct data fields.

We can now use this template in our internal tools. For example, we could have a system that automatically takes the raw JSON from our voice analytics service, renders this template, and posts the summary to a Slack channel for the product team to review. This would significantly speed up our feedback analysis process.
