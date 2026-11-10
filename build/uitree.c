#include "uitree.h"
#include <stdarg.h>

UITreeNodeDictEntryList* NewUITreeNodeDictEntryList()
{
	UITreeNodeDictEntryList* del = malloc(sizeof(UITreeNodeDictEntryList));
	InitUITreeNodeDictEntryList(del);
	return del;
}

UITreeNodeDictEntry* NewUITreeNodeDictEntry(char* key, PythonDictValueRepresentation* value)
{
	UITreeNodeDictEntry* e = malloc(sizeof(UITreeNodeDictEntry));
	if (e == NULL)
	{
		printf("error while allocating memory for UITreeNodeDictEntry\n");
		exit(1);
	}
	e->key = key;
	e->value = value;
	return e;
}

void InitUITreeNodeDictEntryList(UITreeNodeDictEntryList* del)
{
	SIZE_T defaultSize = 256;
	del->data = malloc(sizeof(UITreeNodeDictEntry*) * defaultSize);
	del->used = 0;
	del->size = defaultSize;
}

void InsertUITreeNodeDictEntry(UITreeNodeDictEntryList* del, UITreeNodeDictEntry* e)
{
	if (del->used == del->size)
	{
		del->size *= 2;
		del->data = realloc(del->data, del->size * sizeof(UITreeNodeDictEntry*));
		if (del->data == NULL)
		{
			printf("unable to realloc data array for UITreeNodeDictEntryList\n");
			exit(1);
		}
	}
	if (del->data == NULL)
	{
		printf("data array for UITreeNodeDictEntryList has become corrupted\n");
		exit(1);
	}
	del->data[del->used++] = e;
}

void FreeUITreeNodeDictEntry(UITreeNodeDictEntry* e)
{
	if (e == NULL)
		return;

	if (e->key != NULL)
	{
		free(e->key);
		e->key = NULL;
	}

	FreePythonDictValueRepresentation(e->value);
	free(e);
	e = NULL;
}

void FreeUITreeNodeDictEntryList(UITreeNodeDictEntryList* del)
{
	if (del == NULL)
		return;

	if (del->data != NULL)
	{
		UINT i;
		for (i = 0; i < del->used; ++i)
		{
			FreeUITreeNodeDictEntry(del->data[i]);
		}
		free(del->data);
		del->data = NULL;
	}

	free(del);
	del = NULL;
}

void FreeUITreeNode(UITreeNode* n)
{
	if (n == NULL)
		return;

	if (n->python_object_type_name != NULL)
	{
		free(n->python_object_type_name);
		n->python_object_type_name = NULL;
	}

	if (n->dict_entries_of_interest != NULL)
		FreeUITreeNodeDictEntryList(n->dict_entries_of_interest);

	if (n->children != NULL)
	{
		UINT i;
		for (i = 0; i < n->number_of_children; ++i)
			FreeUITreeNode(n->children[i]);
		free(n->children);
		n->children = NULL;
	}

	free(n);
	n = NULL;
}

/* ---- Safe string builder (fix 2026-11-10) ----
 * Phien ban cu dung sprintf_s(response, size, "%s...", response) — TU ALIAS
 * dest/src trong cung mot buffer = UB: JSON bi rac/trung doan ("Extra data",
 * "char 0", "]}") khi cay UI lon (JobBoard ~470KB). Thay bang SB giong dsb:
 * realloc khi can, khong bao gio tu-alias, khong tran 500000 bytes.
 */
typedef struct {
	char* buf;
	size_t len;
	size_t cap;
	int ok;
} SB;

static void sb_init(SB* s)
{
	s->cap = 4096;
	s->len = 0;
	s->ok = 1;
	s->buf = (char*)malloc(s->cap);
	if (s->buf == NULL) { s->ok = 0; s->cap = 0; return; }
	s->buf[0] = '\0';
}

static void sb_free(SB* s)
{
	if (s->buf != NULL) free(s->buf);
	s->buf = NULL;
	s->len = 0;
	s->cap = 0;
}

static void sb_vappendf(SB* s, const char* fmt, va_list ap)
{
	if (!s->ok) return;
	char tmp[16384];
	int need = vsnprintf(tmp, sizeof(tmp), fmt, ap);
	if (need < 0) { s->ok = 0; return; }
	if ((size_t)need >= sizeof(tmp)) need = (int)sizeof(tmp) - 1;
	size_t required = s->len + (size_t)need + 1;
	if (required > s->cap)
	{
		size_t newcap = s->cap * 2;
		while (newcap < required) newcap *= 2;
		char* nb = (char*)realloc(s->buf, newcap);
		if (nb == NULL) { s->ok = 0; return; }
		s->buf = nb;
		s->cap = newcap;
	}
	memcpy(s->buf + s->len, tmp, (size_t)need + 1);
	s->len += (size_t)need;
}

static void sb_appendf(SB* s, const char* fmt, ...)
{
	va_list ap;
	va_start(ap, fmt);
	sb_vappendf(s, fmt, ap);
	va_end(ap);
}

char* PrintUITreeNodeDictEntryList(UITreeNodeDictEntryList* del)
{
	SB sb;
	sb_init(&sb);
	if (del == NULL)
		return sb.buf;
	UINT i;
	for (i = 0; i < del->used; ++i)
	{
		if (del->data[i] == NULL || del->data[i]->key == NULL || del->data[i]->value == NULL)
			continue;
		ULONGLONG entry_addr = (ULONGLONG)del->data[i];
		ULONGLONG key_addr = (ULONGLONG)del->data[i]->key;
		ULONGLONG val_addr = (ULONGLONG)del->data[i]->value;
		if (entry_addr < 0x10000 || entry_addr > 0x7FFFFFFF0000ULL
			|| key_addr < 0x10000 || key_addr > 0x7FFFFFFF0000ULL
			|| val_addr < 0x10000 || val_addr > 0x7FFFFFFF0000ULL)
		{
			fprintf(stderr, "[Z] BAD entry %d/%d e=%I64x k=%I64x v=%I64x\n",
				(int)i, (int)del->used, entry_addr, key_addr, val_addr);
			continue;
		}

		// print the key
		sb_appendf(&sb, "\"%s\": ", del->data[i]->key);

		// print the value
		if (del->data[i]->value->is_string)
			sb_appendf(&sb, "\"%s\",", del->data[i]->value->string_value);
		else if (del->data[i]->value->is_unicode)
			sb_appendf(&sb, "\"%s\",", del->data[i]->value->unicode_value);
		else if (del->data[i]->value->is_int)
			sb_appendf(&sb, "%d,", del->data[i]->value->int_value);
		else if (del->data[i]->value->is_float)
			sb_appendf(&sb, "%f,", del->data[i]->value->float_value);
		else if (del->data[i]->value->is_bool)
			sb_appendf(&sb, "%s,", del->data[i]->value->bool_value ? "true" : "false");
		else
			sb_appendf(&sb, "null,");
	}
	if (sb.len == 0 || !sb.ok)
		return sb.buf;
	if (sb.buf[sb.len - 1] == ',')
		sb.buf[sb.len - 1] = '\0';
	return sb.buf;
}

static void sb_print_node(UITreeNode* n, int level, SB* out)
{
	if (n == NULL || !out->ok)
		return;
	sb_appendf(out, "{");
	sb_appendf(out, "\"address\": %I64u,", n->address);
	sb_appendf(out, "\"type\": \"%s\",", n->python_object_type_name);
	sb_appendf(out, "\"attrs\": {");
	if (n->dict_entries_of_interest != NULL && n->dict_entries_of_interest->used > 0)
	{
		char* dict_response = PrintUITreeNodeDictEntryList(n->dict_entries_of_interest);
		if (dict_response != NULL)
		{
			sb_appendf(out, "%s", dict_response);
			free(dict_response);
		}
	}
	sb_appendf(out, "},");
	sb_appendf(out, "\"children\": [");
	UINT i;
	for (i = 0; i < n->number_of_children; ++i)
	{
		if (n->children[i] != NULL)
		{
			size_t len_before_child = out->len;
			int ok_before_child = out->ok;
			sb_print_node(n->children[i], level + 1, out);
			size_t emitted = out->len - len_before_child;
			if (emitted == 0 && ok_before_child)
				fprintf(stderr, "[Z] zero-emit child %d/%d parent=%I64u child=%I64u\n",
					(int)i, (int)n->number_of_children, n->address, n->children[i]->address);
			if (i < n->number_of_children - 1)
				sb_appendf(out, ",");
		}
	}
	sb_appendf(out, "]}");
	if (level == 0)
		sb_appendf(out, "\n");
}

char* PrintUITreeNode(UITreeNode* n, int level)
{
	SB out;
	sb_init(&out);
	sb_print_node(n, level, &out);
	if (!out.ok)
	{
		sb_free(&out);
		char* failed = (char*)malloc(3);
		if (failed != NULL) strcpy_s(failed, 3, "{}");
		return failed;
	}
	return out.buf;
}

