"use strict";

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
