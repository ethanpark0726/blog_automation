---
layout: page
title: "📂 Dad Mode Posts"
permalink: /dad/
description: "친근하고 쉬운 설명의 아빠 모드 포스트 모음"
---

<div class="category-page">
  <div class="category-header">
    <h1>👨‍👧 아빠 모드 포스트</h1>
    <p>초등학생도 이해할 수 있는 쉽고 재미있는 기술 이야기</p>
  </div>

  {% assign dad_posts = site.posts | where_exp: "post", "post.categories contains 'Dad'" %}
  {% if dad_posts.size > 0 %}
    <div class="post-list">
      {% for post in dad_posts %}
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
    <p class="no-posts">아직 포스트가 없습니다. 텔레그램 봇에 질문을 보내보세요! 🤖</p>
  {% endif %}
</div>
