
const uploadForm = document.getElementById("uploadForm");
const fileInput = document.getElementById("fileInput");
const fileLabel = document.getElementById("fileLabel");
const uploadButton = document.getElementById("uploadButton");
const uploadResult = document.getElementById("uploadResult");

const downloadForm = document.getElementById("downloadForm");
const codeInput = document.getElementById("codeInput");
const downloadResult = document.getElementById("downloadResult");

// Display the selected filename.
fileInput.addEventListener("change", () => {
    fileLabel.textContent = fileInput.files.length
        ? fileInput.files[0].name
        : "Choose a file from your device";
});

// Upload a file and receive a sharing code.
uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const file = fileInput.files[0];

    if (!file) {
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    uploadButton.disabled = true;
    uploadButton.textContent = "Uploading...";
    uploadResult.hidden = false;
    uploadResult.textContent = "Please wait...";

    try {
        const response = await fetch("/api/upload", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Upload failed.");
        }

        uploadResult.textContent =
            `Your sharing code is: ${data.code}`;
    } catch (error) {
        uploadResult.textContent =
            error.message || "Something went wrong.";
    } finally {
        uploadButton.disabled = false;
        uploadButton.textContent = "Upload and get code";
    }
});

// Find a file using its sharing code.
downloadForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const code = codeInput.value.trim().toUpperCase();

    if (!/^[A-Z0-9]{6}$/.test(code)) {
        downloadResult.hidden = false;
        downloadResult.textContent =
            "Enter a valid 6-character code.";
        return;
    }

    downloadResult.hidden = false;
    downloadResult.textContent = "Checking code...";

    try {
        const response = await fetch(
            `/api/files/${encodeURIComponent(code)}`
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "File not found.");
        }

        downloadResult.replaceChildren();

        const message = document.createElement("p");
        message.textContent = `File found: ${data.filename}`;

        const link = document.createElement("a");
        link.href = `/download/${encodeURIComponent(code)}`;
        link.textContent = "Download file";
        link.className = "download-link";

        downloadResult.append(message, link);
    } catch (error) {
        downloadResult.textContent =
            error.message || "Something went wrong.";
    }
});
