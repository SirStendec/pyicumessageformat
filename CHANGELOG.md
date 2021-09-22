# 1.0.0

* Added: `tag_prefix` option that requires all tag names to start
  with a specific string to be matched. Does not function with
  `strict_tags` enabled.

* Changed: In loose tags mode, the string `</` will not be matched
  if not followed with a letter to start a tag name.


# 0.4.0

* Added: `strict_tags` option that requires all tag characters to be
  escaped if not part of a tag name.

* Changed: With the new `strict_tags` setting, it has been set to False
  by default. As such, usage of the `<` character when tags are enabled
  but outside of a tag is easier. For example, the following string
  will be parsed as text with `strict_tags` set to False, but will throw
  an exception if `strict_tags` is True: `I <3 Python`


# 0.3.0

* Added: `maximum_depth` option that prevents parsing from recursing past
  a set limit. By default, the maximum depth is `50`.

* Fixed: Rethrow `RecursionError` as `SyntaxError` because any time we hit
  a recursion error it is due to having too many nested sub-messages. This
  should never be an issue because of the new maximum depth check, but
  exists to handle edge cases where the call stack is already immense.


# 0.2.1

* Fixed: Incorrect end index returned for hash placeholders.


# 0.2.0

* Added: `include_indices` option that includes `start` and `end` indexes
  for every placeholder.

* Changed: Hash placeholders now have `hash: True` on their objects.


# 0.1.1

* Fixed: Several locations where an `IndexError` could be raised rather than
  `SyntaxError` due to poorly formatted source strings.

* Changed: Ensure that any `IndexError`s are re-thrown as `SyntaxError`s.
  While not perfect, this is effectively true enough.
