/**
 * SVG Map Enhancer
 * Adds responsiveness, interactivity, animations, zoom/pan functionality,
 * and accessibility features to SVG maps.
 */
class SVGMapEnhancer {
  constructor(svgElement, options = {}) {
    this.svg =
      typeof svgElement === "string"
        ? document.querySelector(svgElement)
        : svgElement;

    if (!this.svg || this.svg.tagName !== "svg") {
      throw new Error("Invalid SVG element provided");
    }

    this.options = {
      zoomFactor: 0.1,
      maxZoom: 5,
      minZoom: 0.5,
      panFactor: 10,
      hoverClass: "svg-hover",
      activeClass: "svg-active",
      tooltipClass: "svg-tooltip",
      enableZoom: true,
      enablePan: true,
      enableTooltips: true,
      ...options,
    };

    this.transform = {
      scale: 1,
      translateX: 0,
      translateY: 0,
    };

    this.isDragging = false;
    this.lastMousePosition = { x: 0, y: 0 };
    this.tooltip = null;

    this.init();
  }

  init() {
    // Make SVG responsive
    this.makeSVGResponsive();

    // Add viewport and content groups for transformation
    this.setupViewport();

    // Add event listeners
    this.addEventListeners();

    // Create tooltip element if enabled
    if (this.options.enableTooltips) {
      this.createTooltip();
    }

    // Add ARIA attributes for accessibility
    this.enhanceAccessibility();
  }

  makeSVGResponsive() {
    if (!this.svg.getAttribute("viewBox")) {
      const width =
        this.svg.getAttribute("width") ||
        this.svg.getBoundingClientRect().width;
      const height =
        this.svg.getAttribute("height") ||
        this.svg.getBoundingClientRect().height;
      this.svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    }

    this.svg.setAttribute("width", "100%");
    this.svg.setAttribute("height", "100%");
    this.svg.style.maxWidth = "100%";
    this.svg.style.height = "auto";
    this.svg.style.display = "block";
  }

  setupViewport() {
    // Preserve existing content
    const contents = Array.from(this.svg.childNodes);

    // Create a group for transformation
    this.viewport = document.createElementNS("http://www.w3.org/2000/svg", "g");
    this.viewport.setAttribute("class", "svg-viewport");

    // Move all content into the new group
    while (this.svg.firstChild) {
      this.viewport.appendChild(this.svg.firstChild);
    }

    this.svg.appendChild(this.viewport);
    this.updateTransform();
  }

  addEventListeners() {
    // Zoom with mouse wheel
    if (this.options.enableZoom) {
      this.svg.addEventListener("wheel", this.handleWheel.bind(this));
    }

    // Pan with mouse drag
    if (this.options.enablePan) {
      this.svg.addEventListener("mousedown", this.handleMouseDown.bind(this));
      document.addEventListener("mousemove", this.handleMouseMove.bind(this));
      document.addEventListener("mouseup", this.handleMouseUp.bind(this));

      // Touch support for mobile
      this.svg.addEventListener("touchstart", this.handleTouchStart.bind(this));
      document.addEventListener("touchmove", this.handleTouchMove.bind(this));
      document.addEventListener("touchend", this.handleTouchEnd.bind(this));
    }

    // Interactive elements (paths, polygons, etc.)
    const interactiveElements = this.svg.querySelectorAll(
      "path, polygon, rect, circle, ellipse"
    );
    interactiveElements.forEach((element) => {
      // Hover effects
      element.addEventListener(
        "mouseenter",
        this.handleElementHover.bind(this)
      );
      element.addEventListener(
        "mouseleave",
        this.handleElementLeave.bind(this)
      );

      // Click events
      element.addEventListener("click", this.handleElementClick.bind(this));

      // Tooltip on hover
      if (this.options.enableTooltips) {
        element.addEventListener("mouseenter", this.showTooltip.bind(this));
        element.addEventListener("mousemove", this.moveTooltip.bind(this));
        element.addEventListener("mouseleave", this.hideTooltip.bind(this));
      }
    });

    // Resize handling for responsiveness
    window.addEventListener("resize", this.handleResize.bind(this));
  }

  updateTransform() {
    this.viewport.setAttribute(
      "transform",
      `translate(${this.transform.translateX}, ${this.transform.translateY}) scale(${this.transform.scale})`
    );
  }

  handleWheel(event) {
    event.preventDefault();

    const direction = event.deltaY < 0 ? 1 : -1;
    const factor = direction * this.options.zoomFactor;

    // Calculate new scale
    let newScale = this.transform.scale * (1 + factor);

    // Apply limits
    newScale = Math.min(
      Math.max(newScale, this.options.minZoom),
      this.options.maxZoom
    );

    // Get mouse position relative to SVG
    const svgRect = this.svg.getBoundingClientRect();
    const mouseX = event.clientX - svgRect.left;
    const mouseY = event.clientY - svgRect.top;

    // Calculate zoom point in current transformed coordinate system
    const zoomPointX =
      (mouseX - this.transform.translateX) / this.transform.scale;
    const zoomPointY =
      (mouseY - this.transform.translateY) / this.transform.scale;

    // Calculate new translate values to zoom at mouse position
    const scaleDiff = newScale - this.transform.scale;
    this.transform.translateX -= zoomPointX * scaleDiff;
    this.transform.translateY -= zoomPointY * scaleDiff;
    this.transform.scale = newScale;

    this.updateTransform();

    // Add smooth transition for zoom
    this.viewport.style.transition = "transform 0.1s ease-out";
    setTimeout(() => {
      this.viewport.style.transition = "";
    }, 100);
  }

  handleMouseDown(event) {
    if (event.button === 0) {
      // Left mouse button
      this.isDragging = true;
      this.lastMousePosition = {
        x: event.clientX,
        y: event.clientY,
      };
      this.svg.style.cursor = "grabbing";
    }
  }

  handleMouseMove(event) {
    if (!this.isDragging) return;

    const dx = event.clientX - this.lastMousePosition.x;
    const dy = event.clientY - this.lastMousePosition.y;

    this.transform.translateX += dx;
    this.transform.translateY += dy;

    this.updateTransform();

    this.lastMousePosition = {
      x: event.clientX,
      y: event.clientY,
    };
  }

  handleMouseUp() {
    this.isDragging = false;
    this.svg.style.cursor = "grab";
  }

  handleTouchStart(event) {
    if (event.touches.length === 1) {
      this.isDragging = true;
      this.lastMousePosition = {
        x: event.touches[0].clientX,
        y: event.touches[0].clientY,
      };
      event.preventDefault();
    }
  }

  handleTouchMove(event) {
    if (!this.isDragging) return;

    const dx = event.touches[0].clientX - this.lastMousePosition.x;
    const dy = event.touches[0].clientY - this.lastMousePosition.y;

    this.transform.translateX += dx;
    this.transform.translateY += dy;

    this.updateTransform();

    this.lastMousePosition = {
      x: event.touches[0].clientX,
      y: event.touches[0].clientY,
    };

    event.preventDefault();
  }

  handleTouchEnd() {
    this.isDragging = false;
  }

  handleElementHover(event) {
    const element = event.target;
    element.classList.add(this.options.hoverClass);

    // Animate hover state
    element.style.transition =
      "fill 0.3s ease, opacity 0.3s ease, transform 0.3s ease";
  }

  handleElementLeave(event) {
    const element = event.target;
    element.classList.remove(this.options.hoverClass);
  }

  handleElementClick(event) {
    const element = event.target;

    // Toggle active class
    const isActive = element.classList.contains(this.options.activeClass);

    // Remove active class from all elements
    const allElements = this.svg.querySelectorAll(
      `.${this.options.activeClass}`
    );
    allElements.forEach((el) => el.classList.remove(this.options.activeClass));

    if (!isActive) {
      element.classList.add(this.options.activeClass);

      // Trigger custom event
      const customEvent = new CustomEvent("svgmapselect", {
        detail: {
          element: element,
          id: element.id,
          data: element.dataset,
        },
      });
      this.svg.dispatchEvent(customEvent);
    }
  }

  createTooltip() {
    this.tooltip = document.createElement("div");
    this.tooltip.className = this.options.tooltipClass;
    this.tooltip.style.position = "absolute";
    this.tooltip.style.display = "none";
    this.tooltip.style.zIndex = "1000";
    this.tooltip.setAttribute("role", "tooltip");
    document.body.appendChild(this.tooltip);
  }

  showTooltip(event) {
    if (!this.tooltip) return;

    const element = event.target;
    const title =
      element.getAttribute("title") ||
      element.getAttribute("data-title") ||
      element.getAttribute("aria-label");

    if (title) {
      element.setAttribute("data-original-title", title);
      element.removeAttribute("title"); // Remove title to prevent default tooltip

      this.tooltip.textContent = title;
      this.tooltip.style.display = "block";
      this.moveTooltip(event);
    }
  }

  moveTooltip(event) {
    if (!this.tooltip || this.tooltip.style.display === "none") return;

    // Position tooltip near cursor
    this.tooltip.style.left = `${event.clientX + 15}px`;
    this.tooltip.style.top = `${event.clientY + 15}px`;
  }

  hideTooltip(event) {
    if (!this.tooltip) return;

    const element = event.target;
    const originalTitle = element.getAttribute("data-original-title");

    if (originalTitle) {
      element.setAttribute("title", originalTitle);
      element.removeAttribute("data-original-title");
    }

    this.tooltip.style.display = "none";
  }

  handleResize() {
    // Ensure SVG remains responsive after window resize
    this.makeSVGResponsive();
  }

  enhanceAccessibility() {
    // Add ARIA attributes to make SVG map accessible
    this.svg.setAttribute("role", "img");

    if (!this.svg.getAttribute("aria-label")) {
      this.svg.setAttribute("aria-label", "Interactive Map");
    }

    // Add keyboard navigation
    this.svg.setAttribute("tabindex", "0");

    // Add keyboard controls for zoom and pan
    this.svg.addEventListener("keydown", (event) => {
      switch (event.key) {
        case "+":
        case "=":
          this.zoom(0.1);
          event.preventDefault();
          break;
        case "-":
          this.zoom(-0.1);
          event.preventDefault();
          break;
        case "ArrowUp":
          this.pan(0, this.options.panFactor);
          event.preventDefault();
          break;
        case "ArrowDown":
          this.pan(0, -this.options.panFactor);
          event.preventDefault();
          break;
        case "ArrowLeft":
          this.pan(this.options.panFactor, 0);
          event.preventDefault();
          break;
        case "ArrowRight":
          this.pan(-this.options.panFactor, 0);
          event.preventDefault();
          break;
        case "Home":
          this.reset();
          event.preventDefault();
          break;
      }
    });

    // Make interactive elements accessible
    const interactiveElements = this.svg.querySelectorAll(
      "path, polygon, rect, circle, ellipse"
    );
    interactiveElements.forEach((element) => {
      if (!element.getAttribute("role")) {
        element.setAttribute("role", "button");
      }

      if (!element.getAttribute("tabindex")) {
        element.setAttribute("tabindex", "0");
      }

      // Add keyboard interaction
      element.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          this.handleElementClick({ target: element });
          event.preventDefault();
        }
      });
    });
  }

  zoom(factor) {
    let newScale = this.transform.scale * (1 + factor);
    newScale = Math.min(
      Math.max(newScale, this.options.minZoom),
      this.options.maxZoom
    );

    // Zoom centered on the SVG
    const svgRect = this.svg.getBoundingClientRect();
    const centerX = svgRect.width / 2;
    const centerY = svgRect.height / 2;

    const zoomPointX =
      (centerX - this.transform.translateX) / this.transform.scale;
    const zoomPointY =
      (centerY - this.transform.translateY) / this.transform.scale;

    const scaleDiff = newScale - this.transform.scale;
    this.transform.translateX -= zoomPointX * scaleDiff;
    this.transform.translateY -= zoomPointY * scaleDiff;
    this.transform.scale = newScale;

    this.updateTransform();
  }

  pan(dx, dy) {
    this.transform.translateX += dx;
    this.transform.translateY += dy;
    this.updateTransform();
  }

  reset() {
    this.transform = {
      scale: 1,
      translateX: 0,
      translateY: 0,
    };

    this.updateTransform();

    // Add transition for smooth reset
    this.viewport.style.transition = "transform 0.3s ease-out";
    setTimeout(() => {
      this.viewport.style.transition = "";
    }, 300);
  }

  // Public API methods
  zoomIn() {
    this.zoom(this.options.zoomFactor);
  }

  zoomOut() {
    this.zoom(-this.options.zoomFactor);
  }

  panTo(x, y) {
    const svgRect = this.svg.getBoundingClientRect();
    const centerX = svgRect.width / 2;
    const centerY = svgRect.height / 2;

    this.transform.translateX = centerX - x * this.transform.scale;
    this.transform.translateY = centerY - y * this.transform.scale;

    this.updateTransform();
  }

  highlightElement(elementId) {
    const element = this.svg.getElementById(elementId);
    if (element) {
      // Clear previous highlights
      const highlighted = this.svg.querySelectorAll(
        `.${this.options.activeClass}`
      );
      highlighted.forEach((el) =>
        el.classList.remove(this.options.activeClass)
      );

      // Add highlight
      element.classList.add(this.options.activeClass);

      // Center the element
      const bbox = element.getBBox();
      const centerX = bbox.x + bbox.width / 2;
      const centerY = bbox.y + bbox.height / 2;
      this.panTo(centerX, centerY);
    }
  }
}

// Export the class
if (typeof module !== "undefined" && module.exports) {
  module.exports = SVGMapEnhancer;
} else {
  window.SVGMapEnhancer = SVGMapEnhancer;
}
