---
layout: default
title: "📂 Trivia Vault"
permalink: /trivia/
description: "A curated storage of general knowledge, interesting science facts, history, and everyday wisdom."
---

<div class="layout-wrapper">
  <main class="main-content">
    <div class="category-page">
      <div class="category-header">
        <h1>💡 Trivia Vault</h1>
        <p>A treasure chest of general knowledge, science trivia, and everyday wisdom</p>
      </div>

      {% assign trivia_posts = site.posts | where_exp: "post", "post.categories contains 'Trivia'" %}
      {% if trivia_posts.size > 0 %}
        <div class="post-list">
          {% for post in trivia_posts %}
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
        <p class="no-posts">No posts yet. Ask the bot on Telegram! 💡</p>
      {% endif %}
    </div>
  </main>
</div>
