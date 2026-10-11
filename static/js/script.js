const uploadForm = document.getElementById("uploadForm");
const fileInput = document.getElementById("fileInput");
const fileLabel = document.getElementById("fileLabel");
const uploadButton = document.getElementById("uploadButton");
const uploadResult = document.getElementById("uploadResult");

const downloadForm = document.getElementById("downloadForm");
const codeInput = document.getElementById("codeInput");
const downloadResult = document.getElementById("downloadResult");

// Show the names of all selected files.
fileInput.addEventListener("change", () => {
  const files = Array.from(fileInput.files);

  if (files.length === 0) {
    fileLabel.textContent = "Choose files from your device";
  } else if (files.length === 1) {
    fileLabel.textContent = files[0].name;
  } else {
    fileLabel.textContent = `${files.length} files selected`;
  }
});

// Upload multiple files together.
uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const files = Array.from(fileInput.files);

  if (files.length === 0) {
    uploadResult.hidden = false;
    uploadResult.textContent = "Please select at least one file.";
    return;
  }

  const formData = new FormData();

  // Send every selected file using the same field name.
  files.forEach((file) => {
    formData.append("files", file);
  });

  uploadButton.disabled = true;
  uploadButton.textContent = "Uploading...";
  uploadResult.hidden = false;
  uploadResult.textContent = "Please wait...";

  try {
    const response = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || data.error || "Upload failed.");
    }

    uploadResult.textContent = `Your sharing code is: ${data.code}`;
  } catch (error) {
    uploadResult.textContent = error.message || "Something went wrong.";
  } finally {
    uploadButton.disabled = false;
    uploadButton.textContent = "Upload and get code";
  }
});

// Find a shared file group using its code.
downloadForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const code = codeInput.value.trim().toUpperCase();

  if (!/^[A-F0-9]{8}$/.test(code)) {
    downloadResult.hidden = false;
    downloadResult.textContent = "Enter a valid 8-character code.";
    return;
  }

  downloadResult.hidden = false;
  downloadResult.textContent = "Checking code...";

  try {
    const response = await fetch(`/api/files/${encodeURIComponent(code)}`);

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Files not found.");
    }

    downloadResult.replaceChildren();

    const message = document.createElement("p");
    message.textContent = `Shared files found: ${data.files.length}`;

    downloadResult.appendChild(message);

    // Show a download link for each file.
    data.files.forEach((file) => {
      const link = document.createElement("a");

      link.href = `/api/download/${encodeURIComponent(code)}/${encodeURIComponent(file.id)}`;

      link.textContent = `Download ${file.filename}`;
      link.className = "download-link";
      link.style.display = "block";

      downloadResult.appendChild(link);
    });
  } catch (error) {
    downloadResult.textContent = error.message || "Something went wrong.";
  }
});
