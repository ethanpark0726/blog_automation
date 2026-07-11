---
layout: default
title: "⚙️ Engineer Mode Posts"
permalink: /engineer/
description: "A collection of Engineer Mode posts with in-depth technical analysis for professional developers"
---

<div class="layout-wrapper">
  <main class="main-content">
    <div class="category-page">
      <div class="category-header">
        <h1>👨‍💻 Engineer Mode Posts</h1>
        <p>In-depth technical analysis for developers and IT professionals</p>
      </div>

      <!-- Language Filter Tabs -->
      <div class="filter-tabs">
        <button class="tab-btn" data-lang="all" onclick="filterPosts('all')">🌏 All</button>
        <button class="tab-btn" data-lang="ko" onclick="filterPosts('ko')">🇰🇷 Korean</button>
        <button class="tab-btn" data-lang="en" onclick="filterPosts('en')">🇺🇸 English</button>
      </div>

      {% assign eng_posts = site.posts | where_exp: "post", "post.categories contains 'Engineer'" %}
      {% if eng_posts.size > 0 %}
        <div class="post-list" id="postGrid">
          {% for post in eng_posts %}
            <article class="post-card" data-lang="{{ post.lang }}">
              <div class="post-card-top">
                <div class="post-badges">
                  <span class="lang-badge lang-{{ post.lang }}">
                    {% if post.lang == 'ko' %}🇰🇷 KO{% else %}🇺🇸 EN{% endif %}
                  </span>
                  <span class="cat-badge cat-engineer">👨‍💻 Engineer</span>
                </div>
                <time class="post-date">{{ post.date | date: "%Y.%m.%d" }}</time>
              </div>

              {% if post.topic_id %}
                {% assign pair_lang = 'en' %}
                {% if post.lang == 'en' %}{% assign pair_lang = 'ko' %}{% endif %}
                {% for p in site.posts %}
                  {% if p.topic_id == post.topic_id and p.lang == pair_lang %}
                    <a href="{{ p.url | relative_url }}" class="pair-link-inline">
                      {% if pair_lang == 'ko' %}🇰🇷 한국어{% else %}🇺🇸 English{% endif %}
                    </a>
                    {% break %}
                  {% endif %}
                {% endfor %}
              {% endif %}

              <h2 class="post-title">
                <a href="{{ post.url | relative_url }}">{{ post.title }}</a>
              </h2>
              {% if post.description %}
                <p class="post-excerpt">{{ post.description }}</p>
              {% endif %}
              <a href="{{ post.url | relative_url }}" class="read-more-btn">Read More →</a>
            </article>
          {% endfor %}
        </div>
      {% else %}
        <p class="no-posts">No posts yet. Send a technical topic to the Telegram bot! 🤖</p>
      {% endif %}
    </div>
  </main>
</div>

<script>
  let currentFilter = 'all';
  function filterPosts(lang) {
    currentFilter = lang;
    const cards = document.querySelectorAll('.post-card');
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(t => t.classList.toggle('active', t.dataset.lang === lang));
    cards.forEach(card => {
      if (lang === 'all' || card.dataset.lang === lang) {
        card.style.display = 'flex';
        card.style.opacity = '0';
        requestAnimationFrame(() => { card.style.transition = 'opacity 0.3s ease'; card.style.opacity = '1'; });
      } else {
        card.style.display = 'none';
      }
    });
    try { localStorage.setItem('blog_lang', lang); } catch(e) {}
  }
  (function() {
    try { const s = localStorage.getItem('blog_lang'); if (s) { filterPosts(s); return; } } catch(e) {}
    const bl = (navigator.language || '').toLowerCase();
    filterPosts(bl.startsWith('ko') ? 'ko' : 'en');
  })();
</script>
