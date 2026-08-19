export function classificationStyle(color) {
  const match = /^#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})$/i.exec(color || "");
  if (!match) return undefined;

  const value = match[1];
  const rgb = value.length <= 4
    ? value.slice(0, 3).split("").map((character) => character.repeat(2)).join("")
    : value.slice(0, 6);
  const normalizedColor = `#${rgb}`;

  return {
    "--classification-color": normalizedColor,
    backgroundColor: `${normalizedColor}18`,
  };
}
