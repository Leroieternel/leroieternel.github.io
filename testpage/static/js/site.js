"use strict";

const taskCarousel = document.querySelector("[data-task-carousel]");

if (taskCarousel) {
  const slides = [...taskCarousel.querySelectorAll(".task-video")];
  const dots = [...taskCarousel.querySelectorAll(".task-dot")];
  const status = taskCarousel.querySelector(".task-carousel-status");
  let activeTask = -1;

  const showTask = (requestedIndex) => {
    const nextIndex = (requestedIndex + slides.length) % slides.length;
    if (nextIndex === activeTask) return;
    slides.forEach((slide, index) => {
      const selected = index === nextIndex;
      if (!selected) slide.querySelector("video").pause();
      slide.hidden = !selected;
      dots[index].setAttribute("aria-current", String(selected));
    });
    activeTask = nextIndex;
    status.textContent = `Task ${activeTask + 1} of ${slides.length}: ${slides[activeTask].dataset.taskName}`;
  };

  taskCarousel.querySelector(".task-carousel-prev").addEventListener("click", () => showTask(activeTask - 1));
  taskCarousel.querySelector(".task-carousel-next").addEventListener("click", () => showTask(activeTask + 1));
  dots.forEach((dot, index) => dot.addEventListener("click", () => showTask(index)));
  taskCarousel.addEventListener("keydown", (event) => {
    // Leave the native video's seeking and volume keyboard shortcuts intact.
    if (!event.target.closest(".task-carousel-arrow, .task-dot") || event.altKey || event.ctrlKey || event.metaKey) return;
    let nextIndex;
    if (event.key === "ArrowLeft") nextIndex = activeTask - 1;
    else if (event.key === "ArrowRight") nextIndex = activeTask + 1;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = slides.length - 1;
    else return;
    event.preventDefault();
    showTask(nextIndex);
    if (event.target.closest(".task-dot")) dots[activeTask].focus();
  });
  showTask(0);
}

// Figures remain ordinary image links when JavaScript is unavailable.
const figureDialog = document.querySelector(".figure-dialog");

if (figureDialog && typeof figureDialog.showModal === "function") {
  const expandedImage = figureDialog.querySelector("img");
  const caption = figureDialog.querySelector("#dialog-caption");
  const closeButton = figureDialog.querySelector(".dialog-close");

  document.querySelectorAll("[data-lightbox]").forEach((link) => {
    link.addEventListener("click", (event) => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      const image = link.querySelector("img");
      expandedImage.src = link.href;
      expandedImage.alt = image.alt;
      caption.textContent = link.closest("figure").querySelector("figcaption").textContent;
      figureDialog.showModal();
      figureDialog.querySelector(".dialog-scroll").scrollTo(0, 0);
      document.body.classList.add("dialog-open");
    });
  });

  closeButton.addEventListener("click", () => figureDialog.close());
  figureDialog.addEventListener("click", (event) => {
    if (event.target !== figureDialog) return;
    const bounds = figureDialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) {
      figureDialog.close();
    }
  });
  figureDialog.addEventListener("close", () => document.body.classList.remove("dialog-open"));
}
