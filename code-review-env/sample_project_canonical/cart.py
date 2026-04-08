def calculate_total(items):
  total=0
  for item in items:
    total += item.get('price', 0)
  return total
