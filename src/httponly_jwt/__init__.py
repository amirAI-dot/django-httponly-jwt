"""
JWT sessions for Django in HttpOnly cookies, renewed by the server so quietly
that the frontend never holds a token.

The design - what the library holds and what it leaves to the project, and
why each piece is built the way it is - is ``docs/design.md``.
"""
