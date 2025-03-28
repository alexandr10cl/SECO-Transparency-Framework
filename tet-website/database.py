SECRET_KEY = 'LabESC'

SQLALCHEMY_DATABASE_URI = \
    '{SGBD}://{user}:{passw}@{server}/{database}'.format(
        SGBD = 'mysql+mysqlconnector',
        user = 'Unirio_admin',
        passw = 'Unirio2025!',
        server = 'transparancy.crigq2wai5zc.sa-east-1.rds.amazonaws.com',
        database = 'tool_portal'
    )

SQLALCHEMY_TRACK_MODIFICATIONS = False