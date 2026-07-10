---
layout: page
title: "⚙️ Engineer Mode Posts"
permalink: /engineer/
description: "A collection of Engineer Mode posts with in-depth technical analysis for professional developers"
---

<div class="category-page">
  <div class="category-header">
    <h1>👨‍💻 Engineer Mode Posts</h1>
    <p>In-depth technical analysis for developers and IT professionals</p>
  </div>

  {% assign eng_posts = site.posts | where_exp: "post", "post.categories contains 'Engineer'" %}
  {% if eng_posts.size > 0 %}
    <div class="post-list">
      {% for post in eng_posts %}
        <article class="post-card">
          <div class="post-card-meta">
            <span class="lang-badge lang-{{ post.lang }}">{{ post.lang | upcase }}</span>
            <span class="post-date">{{ post.date | date: "%Y.%m.%d" }}</span>
          </div>
          <h2><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h2>
          {% if post.description %}
            <p class="post-excerpt">{{ post.description }}</p>
          {% endif %}
          <a href="{{ post.url | relative_url }}" class="read-more">Read More →</a>
        </article>
      {% endfor %}
    </div>
  {% else %}
    <p class="no-posts">No posts yet. Send a technical topic to the Telegram bot! 🤖</p>
  {% endif %}
</div>
