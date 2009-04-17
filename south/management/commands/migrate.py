from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.conf import settings
from django.db import models
from optparse import make_option
from south import migration
import sys

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--all', action='store_true', dest='all_apps', default=False,
            help='Run the specified migration for all apps.'),
        make_option('--list', action='store_true', dest='list', default=False,
            help='List migrations noting those that have been applied'),
        make_option('--skip', action='store_true', dest='skip', default=False,
            help='Will skip over out-of-order missing migrations'),
        make_option('--merge', action='store_true', dest='merge', default=False,
            help='Will run out-of-order missing migrations as they are - no rollbacks.'),
        make_option('--no-initial-data', action='store_true', dest='no_initial_data', default=False,
            help='Skips loading initial data if specified.'),
        make_option('--only', action='store_true', dest='only', default=False,
            help='Only runs or rolls back the migration specified, and none around it.'),
        make_option('--fake', action='store_true', dest='fake', default=False,
            help="Pretends to do the migrations, but doesn't actually execute them."),
        make_option('--db-dry-run', action='store_true', dest='db_dry_run', default=False,
            help="Doesn't execute the SQL generated by the db methods, and doesn't store a record that the migration(s) occurred. Useful to test migrations before applying them."),
    )
    if '--verbosity' not in [opt.get_opt_string() for opt in BaseCommand.option_list]:
        option_list += (
            make_option('--verbosity', action='store', dest='verbosity', default='1',
            type='choice', choices=['0', '1', '2'],
            help='Verbosity level; 0=minimal output, 1=normal output, 2=all output'),
        )
    help = "Runs migrations for all apps."

    def handle(self, app=None, target=None, skip=False, merge=False, only=False, backwards=False, fake=False, db_dry_run=False, list=False, **options):

        # Work out what the resolve mode is
        resolve_mode = merge and "merge" or (skip and "skip" or None)
        # Turn on db debugging
        from south.db import db
        db.debug = True
        
        # NOTE: THIS IS DUPLICATED FROM django.core.management.commands.syncdb
        # This code imports any module named 'management' in INSTALLED_APPS.
        # The 'management' module is the preferred way of listening to post_syncdb
        # signals, and since we're sending those out with create_table migrations,
        # we need apps to behave correctly.
        for app_name in settings.INSTALLED_APPS:
            try:
                __import__(app_name + '.management', {}, {}, [''])
            except ImportError, exc:
                msg = exc.args[0]
                if not msg.startswith('No module named') or 'management' not in msg:
                    raise
        # END DJANGO DUPE CODE
        
        # if all_apps flag is set, shift app over to target
        if options['all_apps']:
            target = app
            app = None

        # Migrate each app
        if app:
            apps = [migration.get_app(app.split(".")[-1])]
        else:
            apps = migration.get_migrated_apps()
        silent = options.get('verbosity', 0) == 0
        
        if list and apps:
            list_migrations(apps)
        
        if not list:
            for app in apps:
                result = migration.migrate_app(
                    app,
                    resolve_mode = resolve_mode,
                    target_name = target,
                    fake = fake,
                    db_dry_run = db_dry_run,
                    silent = silent,
                    load_inital_data = not options['no_initial_data'],
                )
                if result is False:
                    return


def list_migrations(apps):
    from south.models import MigrationHistory
    apps = list(apps)
    names = [migration.get_app_name(app) for app in apps]
    applied_migrations = MigrationHistory.objects.filter(app_name__in=names)
    applied_migrations = ['%s.%s' % (mi.app_name,mi.migration) for mi in applied_migrations]

    print
    for app in apps:
        print migration.get_app_name(app)
        all_migrations = migration.get_migration_names(app)
        for migration_name in all_migrations:
            long_form = '%s.%s' % (migration.get_app_name(app),migration_name)
            if long_form in applied_migrations:
                print format_migration_list_item(migration_name)
            else:
                print format_migration_list_item(migration_name, applied=False)
        print


def format_migration_list_item(name, applied=True):
    if applied:
        return '   * %s' % name
    return '     %s' % name
