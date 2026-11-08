---
layout: post
title: "The Optical Illusion of Interference: Understanding Moiré Patterns"
date: 2026-11-09 02:58:26 +0900
categories: [Trivia]
tags:
  - optics
  - physics
  - photography
  - printing
  - moiré
  - aliasing
lang: en
topic_id: "moiré-pattern"
post_id: "moiré-pattern-0faff6eb"
request_fingerprint: "e78c2b6643a0d0465382"
description: "An exploration of Moiré patterns, covering the physics of spatial interference, historical textile origins, and how to mitigate digital aliasing."
---

# The Optical Illusion of Interference: Understanding Moiré Patterns

In the world of visual arts, printing, and digital displays, there is an elusive phenomenon that often appears as an unwanted guest: the Moiré pattern. Whether you have noticed it while taking a photo of a computer screen or seen it in the shimmering fabric of a silk dress, Moiré patterns are a fascinating intersection of geometry, wave physics, and digital sampling.

## The Mechanics of Moiré: How Interference Occurs

At its core, a Moiré pattern is a large-scale wave interference pattern created when two partially opaque, repetitive patterns are overlaid. This is not a physical change to the objects themselves, but rather an optical effect created by the interaction of the two grids.

The mechanism relies on the spatial frequency of the two patterns. When two repetitive structures—such as lines, dots, or grids—are superimposed at a slight angle, displaced, or possess slightly different pitches, they create a new, larger-scale pattern that is visible to the human eye. 

Think of it as a "beat phenomenon" in the spatial domain. Just as two sound waves of slightly different frequencies create a pulsing volume (an acoustic beat), two spatial patterns of slightly different densities create a visible "beat" in the form of dark and light fringes.

### The Mathematics of the Interference
When two sets of parallel lines with spacing $d_1$ and $d_2$ are overlaid at an angle $\theta$, the resulting Moiré fringes have a spacing $D$ that can be approximated by:

$$D = \frac{d_1 d_2}{\sqrt{d_1^2 + d_2^2 - 2d_1 d_2 \cos(\theta)}}$$

As the angle $\theta$ approaches zero, the spacing $D$ becomes significantly larger, which is why even a tiny misalignment can create massive, distracting patterns.

## Historical Context and Etymology

The term "Moiré" originates from the French word for a type of textile, typically silk, which has a wavy or "watered" appearance. This fabric, known as *moire* (or sometimes *moiré*), is processed using a technique called "calendaring," where the fabric is pressed between heated rollers. The alignment of the fibers during this process creates natural interference patterns that shift as the fabric moves, giving it a luxurious, shimmering quality.

In the 20th century, as printing technology moved toward halftone processes—using small dots to represent continuous tones—Moiré patterns became a common technical hurdle. Printers had to carefully calculate "screen angles" for CMYK color layers to ensure that the dot patterns did not interfere with one another, which would otherwise result in unsightly, muddy patterns on the final print.

## Comparison: Moiré in Different Media

To understand where Moiré patterns emerge, we can compare their manifestations across various fields:

| Field | Cause of Moiré | Typical Consequence |
| :--- | :--- | :--- |
| **Printing** | Misalignment of halftone screens | "Rosette" patterns or color banding |
| **Digital Photography** | Sensor grid vs. subject detail | "Aliasing" or rainbow artifacts |
| **Displays (LCD/OLED)** | Sub-pixel grid vs. screen resolution | Shimmering lines on fine textures |
| **Physics/Optics** | Superposition of wave-fronts | Interference fringes in lasers |

## Practical Examples and Mitigation

Moiré patterns are rarely desired in modern technology, often representing a failure of spatial resolution. Here are the most common scenarios where you might encounter them:

### Digital Photography (The Aliasing Problem)
When you point a camera at a subject with very fine, repetitive lines—like a window screen or a finely woven shirt—the camera's sensor grid may conflict with the pattern of the subject. If the subject's detail is finer than the sensor's pixel pitch, the camera interprets the pattern incorrectly, resulting in "aliasing," where different signals become indistinguishable due to undersampling.

**Mitigation:** 
*   **Optical Low-Pass Filters (OLPF):** Many professional cameras include a filter that slightly blurs the image at the pixel level to prevent the sensor from resolving patterns that are too fine.
*   **Post-Processing:** Software like Adobe Lightroom or Photoshop includes "Moiré reduction" tools, which target the specific color-fringe patterns associated with aliasing.

### Screen Recording
Have you ever tried to record a video of your monitor using a smartphone? You likely saw a series of wavy, shifting bands across the screen. This is a classic Moiré pattern caused by the interference between the pixels of your monitor and the pixel array of your phone's camera sensor.

**Mitigation:**
*   **Change the distance:** Adjusting the distance between the camera and the screen changes the effective resolution, which can often break the interference pattern.
*   **Angle adjustment:** Tilting the camera slightly can shift the alignment, effectively eliminating the Moiré effect.

## References

- [Moiré pattern](https://en.wikipedia.org/wiki/Moir%C3%A9%20pattern)
- [Line moiré](https://en.wikipedia.org/wiki/Line%20moir%C3%A9)
- [Moire (disambiguation)](https://en.wikipedia.org/wiki/Moire%20%28disambiguation%29)
- [Scott Moir](https://en.wikipedia.org/wiki/Scott%20Moir)
- [High Speed Photography On Moire Pattern Masked Flight Target](https://doi.org/10.1117/12.968013)
- [Moire pattern](https://doi.org/10.1036/1097-8542.429500)
- [Moire pattern](https://doi.org/10.1007/springerreference_19169)