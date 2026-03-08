(() => {
  const DEFAULT_DATASET_ID = "3_2_3_17_77_19_10_1_1";

  const getPropertyGeometry = (payload) =>
    payload?.mss_profile?.msn_profile?.fnd_profile?.property?.geometry || null;

  const collectPolygons = (geometry) => {
    if (!geometry) {
      return [];
    }
    if (geometry.type === "Polygon") {
      return [geometry.coordinates];
    }
    if (geometry.type === "MultiPolygon") {
      return geometry.coordinates;
    }
    return [];
  };

  const normalizePoints = (points) =>
    points
      .map(([lon, lat]) => [Number(lon), Number(lat)])
      .filter(([lon, lat]) => Number.isFinite(lon) && Number.isFinite(lat));

  const createSvgElement = (tag, attrs = {}) => {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.entries(attrs).forEach(([key, value]) => {
      el.setAttribute(key, value);
    });
    return el;
  };

  const renderPolygons = (container, polygons) => {
    const allPoints = polygons.flatMap((polygon) =>
      normalizePoints(Array.isArray(polygon) ? polygon[0] || [] : [])
    );
    if (allPoints.length < 3) {
      throw new Error("Polygon coordinates are missing or invalid.");
    }

    const lons = allPoints.map((point) => point[0]);
    const lats = allPoints.map((point) => point[1]);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);

    const width = maxLon - minLon || 1;
    const height = maxLat - minLat || 1;
    const paddingRatio = 0.08;
    const paddedWidth = width * (1 + paddingRatio * 2);
    const paddedHeight = height * (1 + paddingRatio * 2);
    const paddedMinLon = minLon - width * paddingRatio;
    const paddedMinLat = minLat - height * paddingRatio;

    const viewBox = [0, 0, paddedWidth, paddedHeight].join(" ");
    const svg = createSvgElement("svg", {
      class: "map-widget__svg",
      viewBox,
      preserveAspectRatio: "xMidYMid meet",
      role: "img",
      "aria-label": "Property boundary",
    });

    polygons.forEach((polygon) => {
      const points = normalizePoints(
        Array.isArray(polygon) ? polygon[0] || [] : []
      );
      if (points.length < 3) {
        return;
      }

      const polygonPoints = points
        .map(([lon, lat]) => {
          const x = lon - paddedMinLon;
          const y = paddedHeight - (lat - paddedMinLat);
          return `${x},${y}`;
        })
        .join(" ");

      const shape = createSvgElement("polygon", {
        points: polygonPoints,
        class: "map-widget__polygon",
      });
      svg.appendChild(shape);
    });

    container.appendChild(svg);
  };

  const renderMessage = (container, message) => {
    container.innerHTML = `<p class="map-widget__message">${message}</p>`;
  };

  const initializeWidget = async () => {
    const container = document.getElementById("map-widget");
    if (!container) {
      return;
    }

    const datasetId = container.dataset.datasetId || DEFAULT_DATASET_ID;

    try {
      const response = await fetch(`/api/datasets/${datasetId}`);
      if (!response.ok) {
        throw new Error(`Dataset request failed (${response.status}).`);
      }

      const payload = await response.json();
      const geometry = getPropertyGeometry(payload);
      const polygons = collectPolygons(geometry);

      if (polygons.length === 0) {
        throw new Error("Property polygon geometry was not found.");
      }

      renderPolygons(container, polygons);
    } catch (error) {
      renderMessage(container, "Property boundary data is unavailable.");
      console.error("Map widget error:", error);
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeWidget);
  } else {
    initializeWidget();
  }
})();
