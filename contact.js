const contact = document.querySelector("[data-contact]");
const reveal = document.createElement("button");
reveal.type = "button";
reveal.textContent = "Reveal email address";
reveal.addEventListener("click", () => {
  const address = ["pleh.mralapool", "moc.kooltuo"]
    .map((part) => [...part].reverse().join(""))
    .join("@");
  const link = document.createElement("a");
  link.href = `mailto:${address}`;
  link.textContent = address;
  contact.replaceChildren(link);
  link.focus();
});
contact.append(reveal);
