---
layout: default
title: "📂 Dad Mode Posts"
permalink: /dad/
description: "A collection of Dad Mode posts with friendly, easy-to-understand explanations"
---

<div class="layout-wrapper">
  <main class="main-content">
    <div class="category-page">
      <div class="category-header">
        <h1>👨‍👧 Dad Mode Posts</h1>
        <p>Easy and fun tech stories that anyone can understand</p>
      </div>

      {% assign dad_posts = site.posts | where_exp: "post", "post.categories contains 'Dad'" %}
      {% if dad_posts.size > 0 %}
        <div class="post-list">
          {% for post in dad_posts %}
            <article class="post-card">
              <div class="post-card-meta" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span class="lang-badge lang-{{ post.lang }}">{{ post.lang | upcase }}</span>
                <span class="post-date">{{ post.date | date: "%Y.%m.%d" }}</span>
              </div>
              <h2><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h2>
              {% if post.description %}
                <p class="post-excerpt" style="margin-top: 8px;">{{ post.description }}</p>
              {% endif %}
              <a href="{{ post.url | relative_url }}" class="read-more" style="display: inline-block; margin-top: 12px;">Read More →</a>
            </article>
          {% endfor %}
        </div>
      {% else %}
        <p class="no-posts">No posts yet. Send a question to the Telegram bot! 🤖</p>
      {% endif %}
    </div>
  </main>
</div>
