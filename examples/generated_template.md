<!DOCTYPE html>
<html>
<head>
  <title>Voice Analytics Transcript Summary</title>
  <style>
    body { font-family: sans-serif; }
    .summary-section { margin-bottom: 20px; }
    .summary-section h2 { color: #333; }
    .summary-section ul { list-style-type: disc; padding-left: 20px; }
  </style>
</head>
<body>

<h1>Voice Analytics Transcript Summary</h1>

<div class="summary-section">
  <h2>Transcript ID: {{ transcript_id }}</h2>
  <p>Customer ID: {{ customer_id }}</p>
  <p>Timestamp: {{ timestamp }}</p>
</div>

<div class="summary-section">
  <h2>Overall Sentiment:</h2>
  <p>{{ sentiment|capitalize }}</p>  {# Capitalizes the sentiment for better readability #}
</div>

<div class="summary-section">
  <h2>Key Topics:</h2>
  <ul>
    {% for topic in key_topics %}
      <li>{{ topic }}</li>
    {% endfor %}
  </ul>
</div>

<div class="summary-section">
  <h2>Conversation Overview:</h2>
  <p>
    {% if full_transcript %}
      {{ full_transcript[:200] }}...  {# Shows the first 200 characters of the transcript for brevity #}
      <a href="#">View Full Transcript</a> { # Placeholder for a link to the full transcript #}
    {% else %}
      No transcript available.
    {% endif %}
  </p>
</div>


</body>
</html>