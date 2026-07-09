---
layout: page
title: "⚙️ Engineer Mode Posts"
permalink: /engineer/
description: "전문 개발자를 위한 기술 심층 분석 포스트 모음"
---

<div class="category-page">
  <div class="category-header">
    <h1>👨‍💻 엔지니어 모드 포스트</h1>
    <p>개발자와 IT 전문가를 위한 심층 기술 분석</p>
  </div>

  {% assign eng_posts = site.posts | where_exp: "post", "post.categories contains 'Engineer'" %}
  {% if eng_posts.size > 0 %}
    <div class="post-list">
      {% for post in eng_posts %}
        <article class="post-card">
          <div class="post-card-meta">
            <span class="lang-badge lang-{{ post.lang }}">{{ post.lang | upcase }}</span>
            <span class="post-date">{{ post.date | date: "%Y년 %m월 %d일" }}</span>
          </div>
          <h2><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h2>
          {% if post.description %}
            <p class="post-excerpt">{{ post.description }}</p>
          {% endif %}
          <a href="{{ post.url | relative_url }}" class="read-more">읽기 →</a>
        </article>
      {% endfor %}
    </div>
  {% else %}
    <p class="no-posts">아직 포스트가 없습니다. 텔레그램 봇에 기술 주제를 보내보세요! 🤖</p>
  {% endif %}
</div>
