from django.db import migrations, models


def backfill_depth(apps, schema_editor):
    Yorum = apps.get_model('posts', 'Yorum')
    parent_map = dict(Yorum.objects.values_list('id', 'parent_id'))
    depth_cache = {}

    def compute_depth(comment_id):
        if comment_id in depth_cache:
            return depth_cache[comment_id]
        path = []
        current = comment_id
        while True:
            if current in depth_cache:
                depth = depth_cache[current]
                break
            parent_id = parent_map.get(current)
            if not parent_id:
                depth = 0
                break
            path.append(current)
            current = parent_id
        for cid in reversed(path):
            depth += 1
            depth_cache[cid] = depth
        if comment_id not in depth_cache:
            depth_cache[comment_id] = depth
        return depth_cache[comment_id]

    all_ids = list(parent_map.keys())
    batch_size = 1000
    for i in range(0, len(all_ids), batch_size):
        batch_ids = all_ids[i:i + batch_size]
        yorumlar = list(Yorum.objects.filter(id__in=batch_ids))
        for yorum in yorumlar:
            yorum.depth = compute_depth(yorum.id)
        Yorum.objects.bulk_update(yorumlar, ['depth'])


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0010_guvenlikihlali'),
    ]

    operations = [
        migrations.AddField(
            model_name='yorum',
            name='depth',
            field=models.IntegerField(default=0),
        ),
        migrations.RunPython(backfill_depth, migrations.RunPython.noop),
    ]
