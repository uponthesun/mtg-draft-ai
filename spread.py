def spread(list_a, list_b):
	total_len = len(list_a) + len(list_b)
	increment = total_len / len(list_a)

	result = [None] * total_len

	i = 0
	for e in list_a:
		result[int(i)] = e
		i += increment

	list_b_copy = list_b.copy()
	for i in range(0, len(result)):
		# Assumes value of list_a are not None
		if result[i] is None:
			result[i] = list_b_copy.pop(0)

	return result

print(spread(['h1'], ['_1', '_2', '_3', '_4', '_5']))
print(spread(['h1', 'h2'], ['_1', '_2', '_3', '_4']))
print(spread(['h1', 'h2', 'h3'], ['_1', '_2', '_3']))
print(spread(['h1', 'h2', 'h3', 'h4'], ['_1', '_2']))
print(spread(['h1', 'h2', 'h3', 'h4', 'h5'], ['_1']))
print(spread(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'], []))