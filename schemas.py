from marshmallow import EXCLUDE, Schema, fields, validate


class CredentialsSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    username = fields.Str(required=True, validate=validate.Length(min=3, max=30))
    password = fields.Str(required=True, validate=validate.Length(min=6, max=72))


class UserSchema(Schema):
    id = fields.Int()
    username = fields.Str()


class NoteSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)
    title = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    content = fields.Str(load_default="")
    category = fields.Str(load_default="general", validate=validate.Length(min=1, max=30))
    is_pinned = fields.Bool(load_default=False)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
