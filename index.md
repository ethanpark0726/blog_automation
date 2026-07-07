---
layout: home
title: "기술 블로그 | Tech Blog"
---

# 🤖 AI 자동화 기술 블로그

텔레그램 한 줄 메시지로 자동 생성되는 **한국어/영어** 기술 블로그입니다.

## 최근 포스트

{% for post in site.posts limit:10 %}
<article class="post-preview">
  <h3><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
  <p class="meta">
    📅 {{ post.date | date: "%Y년 %m월 %d일" }} &nbsp;|&nbsp;
    🌐 {{ post.lang | upcase }} &nbsp;|&nbsp;
    🏷️ {{ post.categories | join: ", " }}
  </p>
  {% if post.description %}
  <p>{{ post.description }}</p>
  {% endif %}
</article>
{% endfor %}
