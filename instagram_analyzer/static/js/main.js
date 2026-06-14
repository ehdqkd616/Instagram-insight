// 검색 폼: Enter 키 즉시 제출
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("input[name='search']").forEach(function (input) {
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        input.closest("form").submit();
      }
    });
  });
});
