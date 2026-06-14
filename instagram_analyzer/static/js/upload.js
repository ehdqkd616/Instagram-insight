document.addEventListener("DOMContentLoaded", function () {
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const fileList  = document.getElementById("fileList");
  const uploadBtn = document.getElementById("uploadBtn");
  const uploadForm = document.getElementById("uploadForm");
  const progress  = document.getElementById("uploadProgress");

  if (!dropZone) return;

  // 드래그 & 드롭
  dropZone.addEventListener("dragover", function (e) {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });
  dropZone.addEventListener("dragleave", function () {
    dropZone.classList.remove("dragover");
  });
  dropZone.addEventListener("drop", function (e) {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    fileInput.files = e.dataTransfer.files;
    updateFileList();
  });

  fileInput.addEventListener("change", updateFileList);

  function updateFileList() {
    const files = fileInput.files;
    if (!files.length) {
      fileList.textContent = "";
      uploadBtn.disabled = true;
      return;
    }
    const names = Array.from(files).map(f => f.name).join(", ");
    fileList.textContent = "선택된 파일: " + names;
    uploadBtn.disabled = false;
  }

  // 업로드 중 진행 바 표시
  uploadForm.addEventListener("submit", function () {
    progress.classList.remove("d-none");
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>업로드 중...';
  });
});
