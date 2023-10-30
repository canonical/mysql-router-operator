let SessionLoad = 1
if &cp | set nocp | endif
let s:cpo_save=&cpo
set cpo&vim
inoremap <silent> <Plug>(ale_complete) :ALEComplete
imap <silent> <C-_>9 <Plug>TComment_9
imap <silent> <C-_>8 <Plug>TComment_8
imap <silent> <C-_>7 <Plug>TComment_7
imap <silent> <C-_>6 <Plug>TComment_6
imap <silent> <C-_>5 <Plug>TComment_5
imap <silent> <C-_>4 <Plug>TComment_4
imap <silent> <C-_>3 <Plug>TComment_3
imap <silent> <C-_>2 <Plug>TComment_2
imap <silent> <C-_>1 <Plug>TComment_1
imap <silent> <C-_>s <Plug>TComment_s
imap <silent> <C-_>n <Plug>TComment_n
imap <silent> <C-_>a <Plug>TComment_a
imap <silent> <C-_>b <Plug>TComment_b
imap <silent> <C-_>i <Plug>TComment_i
imap <silent> <C-_>r <Plug>TComment_r
imap <silent> <C-_>  <Plug>TComment_ 
imap <silent> <C-_>p <Plug>TComment_p
imap <silent> <C-_><C-_> <Plug>TComment_
inoremap <Plug>TComment_<C-_>9 :call tcomment#SetOption("count", 9)
inoremap <Plug>TComment_9 :call tcomment#SetOption("count", 9)
inoremap <Plug>TComment_<C-_>8 :call tcomment#SetOption("count", 8)
inoremap <Plug>TComment_8 :call tcomment#SetOption("count", 8)
inoremap <Plug>TComment_<C-_>7 :call tcomment#SetOption("count", 7)
inoremap <Plug>TComment_7 :call tcomment#SetOption("count", 7)
inoremap <Plug>TComment_<C-_>6 :call tcomment#SetOption("count", 6)
inoremap <Plug>TComment_6 :call tcomment#SetOption("count", 6)
inoremap <Plug>TComment_<C-_>5 :call tcomment#SetOption("count", 5)
inoremap <Plug>TComment_5 :call tcomment#SetOption("count", 5)
inoremap <Plug>TComment_<C-_>4 :call tcomment#SetOption("count", 4)
inoremap <Plug>TComment_4 :call tcomment#SetOption("count", 4)
inoremap <Plug>TComment_<C-_>3 :call tcomment#SetOption("count", 3)
inoremap <Plug>TComment_3 :call tcomment#SetOption("count", 3)
inoremap <Plug>TComment_<C-_>2 :call tcomment#SetOption("count", 2)
inoremap <Plug>TComment_2 :call tcomment#SetOption("count", 2)
inoremap <Plug>TComment_<C-_>1 :call tcomment#SetOption("count", 1)
inoremap <Plug>TComment_1 :call tcomment#SetOption("count", 1)
inoremap <Plug>TComment_<C-_>s :TCommentAs =&ft_
inoremap <Plug>TComment_s :TCommentAs =&ft_
inoremap <Plug>TComment_<C-_>n :TCommentAs =&ft 
inoremap <Plug>TComment_n :TCommentAs =&ft 
inoremap <Plug>TComment_<C-_>a :TCommentAs 
inoremap <Plug>TComment_a :TCommentAs 
inoremap <Plug>TComment_<C-_>b :TCommentBlock mode=#
inoremap <Plug>TComment_b :TCommentBlock mode=#
inoremap <Plug>TComment_<C-_>i v:TCommentInline mode=#
inoremap <Plug>TComment_i v:TCommentInline mode=#
inoremap <Plug>TComment_<C-_>r :TCommentRight
inoremap <Plug>TComment_r :TCommentRight
inoremap <Plug>TComment_<C-_>  :TComment 
inoremap <Plug>TComment_  :TComment 
inoremap <Plug>TComment_<C-_>p :norm! m`vip:TComment``
inoremap <Plug>TComment_p :norm! m`vip:TComment``
inoremap <Plug>TComment_<C-_><C-_> :TComment
inoremap <Plug>TComment_ :TComment
imap <S-Tab> <Plug>SuperTabBackward
inoremap <C-Tab> 	
map  :NERDTreeFind
nmap <silent> 	 :wincmd t
map  :TagbarToggle
map  :NERDTreeToggle
nmap <silent>  :vs|:b#
nmap <silent>  :wincmd x
vmap <silent> 9 <Plug>TComment_9
nmap <silent> 9 <Plug>TComment_9
omap <silent> 9 <Plug>TComment_9
vmap <silent> 8 <Plug>TComment_8
nmap <silent> 8 <Plug>TComment_8
omap <silent> 8 <Plug>TComment_8
vmap <silent> 7 <Plug>TComment_7
nmap <silent> 7 <Plug>TComment_7
omap <silent> 7 <Plug>TComment_7
vmap <silent> 6 <Plug>TComment_6
nmap <silent> 6 <Plug>TComment_6
omap <silent> 6 <Plug>TComment_6
vmap <silent> 5 <Plug>TComment_5
nmap <silent> 5 <Plug>TComment_5
omap <silent> 5 <Plug>TComment_5
vmap <silent> 4 <Plug>TComment_4
nmap <silent> 4 <Plug>TComment_4
omap <silent> 4 <Plug>TComment_4
vmap <silent> 3 <Plug>TComment_3
nmap <silent> 3 <Plug>TComment_3
omap <silent> 3 <Plug>TComment_3
vmap <silent> 2 <Plug>TComment_2
nmap <silent> 2 <Plug>TComment_2
omap <silent> 2 <Plug>TComment_2
vmap <silent> 1 <Plug>TComment_1
nmap <silent> 1 <Plug>TComment_1
omap <silent> 1 <Plug>TComment_1
map <silent> ca <Plug>TComment_ca
map <silent> cc <Plug>TComment_cc
map <silent> s <Plug>TComment_s
map <silent> n <Plug>TComment_n
map <silent> a <Plug>TComment_a
map <silent> b <Plug>TComment_b
map <silent> i <Plug>TComment_i
map <silent> r <Plug>TComment_r
map <silent>   <Plug>TComment_ 
map <silent> p <Plug>TComment_p
vmap <silent>  <Plug>TComment_
nmap <silent>  <Plug>TComment_
omap <silent>  <Plug>TComment_
map <silent> \_s <Plug>TComment_\_s
map <silent> \_n <Plug>TComment_\_n
map <silent> \_a <Plug>TComment_\_a
map <silent> \_b <Plug>TComment_\_b
map <silent> \_r <Plug>TComment_\_r
xmap <silent> \_i <Plug>TComment_\_i
map <silent> \_  <Plug>TComment_\_ 
map <silent> \_p <Plug>TComment_\_p
xmap <silent> \__ <Plug>TComment_\__
nmap <silent> \__ <Plug>TComment_\__
smap <silent> \__ <Plug>TComment_\__
omap <silent> \__ <Plug>TComment_\__
xmap gx <Plug>NetrwBrowseXVis
nmap gx <Plug>NetrwBrowseX
xmap <silent> g> <Plug>TComment_Comment
nmap <silent> g>b <Plug>TComment_Commentb
nmap <silent> g>c <Plug>TComment_Commentc
nmap <silent> g> <Plug>TComment_Comment
xmap <silent> g< <Plug>TComment_Uncomment
nmap <silent> g<b <Plug>TComment_Uncommentb
nmap <silent> g<c <Plug>TComment_Uncommentc
nmap <silent> g< <Plug>TComment_Uncomment
xmap <silent> gc <Plug>TComment_gc
nmap <silent> gcb <Plug>TComment_gcb
nmap <silent> gcc <Plug>TComment_gcc
nmap <silent> gc9c <Plug>TComment_gc9c
nmap <silent> gc9 <Plug>TComment_gc9
nmap <silent> gc8c <Plug>TComment_gc8c
nmap <silent> gc8 <Plug>TComment_gc8
nmap <silent> gc7c <Plug>TComment_gc7c
nmap <silent> gc7 <Plug>TComment_gc7
nmap <silent> gc6c <Plug>TComment_gc6c
nmap <silent> gc6 <Plug>TComment_gc6
nmap <silent> gc5c <Plug>TComment_gc5c
nmap <silent> gc5 <Plug>TComment_gc5
nmap <silent> gc4c <Plug>TComment_gc4c
nmap <silent> gc4 <Plug>TComment_gc4
nmap <silent> gc3c <Plug>TComment_gc3c
nmap <silent> gc3 <Plug>TComment_gc3
nmap <silent> gc2c <Plug>TComment_gc2c
nmap <silent> gc2 <Plug>TComment_gc2
nmap <silent> gc1c <Plug>TComment_gc1c
nmap <silent> gc1 <Plug>TComment_gc1
nmap <silent> gc <Plug>TComment_gc
omap <silent> ic <Plug>TComment_ic
vmap <silent> ic <Plug>TComment_ic
xnoremap <silent> <Plug>NetrwBrowseXVis :call netrw#BrowseXVis()
nnoremap <silent> <Plug>NetrwBrowseX :call netrw#BrowseX(netrw#GX(),netrw#CheckIfRemote(netrw#GX()))
nnoremap <silent> <Plug>(ale_repeat_selection) :ALERepeatSelection
nnoremap <silent> <Plug>(ale_code_action) :ALECodeAction
nnoremap <silent> <Plug>(ale_filerename) :ALEFileRename
nnoremap <silent> <Plug>(ale_rename) :ALERename
nnoremap <silent> <Plug>(ale_import) :ALEImport
nnoremap <silent> <Plug>(ale_documentation) :ALEDocumentation
nnoremap <silent> <Plug>(ale_hover) :ALEHover
nnoremap <silent> <Plug>(ale_find_references) :ALEFindReferences
nnoremap <silent> <Plug>(ale_go_to_implementation_in_vsplit) :ALEGoToImplementation -vsplit
nnoremap <silent> <Plug>(ale_go_to_implementation_in_split) :ALEGoToImplementation -split
nnoremap <silent> <Plug>(ale_go_to_implementation_in_tab) :ALEGoToImplementation -tab
nnoremap <silent> <Plug>(ale_go_to_implementation) :ALEGoToImplementation
nnoremap <silent> <Plug>(ale_go_to_type_definition_in_vsplit) :ALEGoToTypeDefinition -vsplit
nnoremap <silent> <Plug>(ale_go_to_type_definition_in_split) :ALEGoToTypeDefinition -split
nnoremap <silent> <Plug>(ale_go_to_type_definition_in_tab) :ALEGoToTypeDefinition -tab
nnoremap <silent> <Plug>(ale_go_to_type_definition) :ALEGoToTypeDefinition
nnoremap <silent> <Plug>(ale_go_to_definition_in_vsplit) :ALEGoToDefinition -vsplit
nnoremap <silent> <Plug>(ale_go_to_definition_in_split) :ALEGoToDefinition -split
nnoremap <silent> <Plug>(ale_go_to_definition_in_tab) :ALEGoToDefinition -tab
nnoremap <silent> <Plug>(ale_go_to_definition) :ALEGoToDefinition
nnoremap <silent> <Plug>(ale_fix) :ALEFix
nnoremap <silent> <Plug>(ale_detail) :ALEDetail
nnoremap <silent> <Plug>(ale_lint) :ALELint
nnoremap <silent> <Plug>(ale_reset_buffer) :ALEResetBuffer
nnoremap <silent> <Plug>(ale_disable_buffer) :ALEDisableBuffer
nnoremap <silent> <Plug>(ale_enable_buffer) :ALEEnableBuffer
nnoremap <silent> <Plug>(ale_toggle_buffer) :ALEToggleBuffer
nnoremap <silent> <Plug>(ale_reset) :ALEReset
nnoremap <silent> <Plug>(ale_disable) :ALEDisable
nnoremap <silent> <Plug>(ale_enable) :ALEEnable
nnoremap <silent> <Plug>(ale_toggle) :ALEToggle
nnoremap <silent> <Plug>(ale_last) :ALELast
nnoremap <silent> <Plug>(ale_first) :ALEFirst
nnoremap <silent> <Plug>(ale_next_wrap_warning) :ALENext -wrap -warning
nnoremap <silent> <Plug>(ale_next_warning) :ALENext -warning
nnoremap <silent> <Plug>(ale_next_wrap_error) :ALENext -wrap -error
nnoremap <silent> <Plug>(ale_next_error) :ALENext -error
nnoremap <silent> <Plug>(ale_next_wrap) :ALENextWrap
nnoremap <silent> <Plug>(ale_next) :ALENext
nnoremap <silent> <Plug>(ale_previous_wrap_warning) :ALEPrevious -wrap -warning
nnoremap <silent> <Plug>(ale_previous_warning) :ALEPrevious -warning
nnoremap <silent> <Plug>(ale_previous_wrap_error) :ALEPrevious -wrap -error
nnoremap <silent> <Plug>(ale_previous_error) :ALEPrevious -error
nnoremap <silent> <Plug>(ale_previous_wrap) :ALEPreviousWrap
nnoremap <silent> <Plug>(ale_previous) :ALEPrevious
vmap <silent> <C-_>9 <Plug>TComment_9
nmap <silent> <C-_>9 <Plug>TComment_9
omap <silent> <C-_>9 <Plug>TComment_9
vmap <silent> <C-_>8 <Plug>TComment_8
nmap <silent> <C-_>8 <Plug>TComment_8
omap <silent> <C-_>8 <Plug>TComment_8
vmap <silent> <C-_>7 <Plug>TComment_7
nmap <silent> <C-_>7 <Plug>TComment_7
omap <silent> <C-_>7 <Plug>TComment_7
vmap <silent> <C-_>6 <Plug>TComment_6
nmap <silent> <C-_>6 <Plug>TComment_6
omap <silent> <C-_>6 <Plug>TComment_6
vmap <silent> <C-_>5 <Plug>TComment_5
nmap <silent> <C-_>5 <Plug>TComment_5
omap <silent> <C-_>5 <Plug>TComment_5
vmap <silent> <C-_>4 <Plug>TComment_4
nmap <silent> <C-_>4 <Plug>TComment_4
omap <silent> <C-_>4 <Plug>TComment_4
vmap <silent> <C-_>3 <Plug>TComment_3
nmap <silent> <C-_>3 <Plug>TComment_3
omap <silent> <C-_>3 <Plug>TComment_3
vmap <silent> <C-_>2 <Plug>TComment_2
nmap <silent> <C-_>2 <Plug>TComment_2
omap <silent> <C-_>2 <Plug>TComment_2
vmap <silent> <C-_>1 <Plug>TComment_1
nmap <silent> <C-_>1 <Plug>TComment_1
omap <silent> <C-_>1 <Plug>TComment_1
map <silent> <C-_>ca <Plug>TComment_ca
map <silent> <C-_>cc <Plug>TComment_cc
map <silent> <C-_>s <Plug>TComment_s
map <silent> <C-_>n <Plug>TComment_n
map <silent> <C-_>a <Plug>TComment_a
map <silent> <C-_>b <Plug>TComment_b
map <silent> <C-_>i <Plug>TComment_i
map <silent> <C-_>r <Plug>TComment_r
map <silent> <C-_>  <Plug>TComment_ 
map <silent> <C-_>p <Plug>TComment_p
vmap <silent> <C-_><C-_> <Plug>TComment_
nmap <silent> <C-_><C-_> <Plug>TComment_
omap <silent> <C-_><C-_> <Plug>TComment_
nnoremap <Plug>TComment_gc9c :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_gc9cg@
nnoremap <Plug>TComment_gc8c :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_gc8cg@
nnoremap <Plug>TComment_gc7c :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_gc7cg@
nnoremap <Plug>TComment_gc6c :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_gc6cg@
nnoremap <Plug>TComment_gc5c :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_gc5cg@
nnoremap <Plug>TComment_gc4c :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_gc4cg@
nnoremap <Plug>TComment_gc3c :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_gc3cg@
nnoremap <Plug>TComment_gc2c :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_gc2cg@
nnoremap <Plug>TComment_gc1c :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_gc1cg@
vnoremap <Plug>TComment_<C-_>9 :call tcomment#SetOption("count", 9)
vnoremap <Plug>TComment_9 :call tcomment#SetOption("count", 9)
nnoremap <Plug>TComment_<C-_>9 :call tcomment#SetOption("count", 9)
onoremap <Plug>TComment_<C-_>9 :call tcomment#SetOption("count", 9)
nnoremap <Plug>TComment_9 :call tcomment#SetOption("count", 9)
onoremap <Plug>TComment_9 :call tcomment#SetOption("count", 9)
vnoremap <Plug>TComment_<C-_>8 :call tcomment#SetOption("count", 8)
vnoremap <Plug>TComment_8 :call tcomment#SetOption("count", 8)
nnoremap <Plug>TComment_<C-_>8 :call tcomment#SetOption("count", 8)
onoremap <Plug>TComment_<C-_>8 :call tcomment#SetOption("count", 8)
nnoremap <Plug>TComment_8 :call tcomment#SetOption("count", 8)
onoremap <Plug>TComment_8 :call tcomment#SetOption("count", 8)
vnoremap <Plug>TComment_<C-_>7 :call tcomment#SetOption("count", 7)
vnoremap <Plug>TComment_7 :call tcomment#SetOption("count", 7)
nnoremap <Plug>TComment_<C-_>7 :call tcomment#SetOption("count", 7)
onoremap <Plug>TComment_<C-_>7 :call tcomment#SetOption("count", 7)
nnoremap <Plug>TComment_7 :call tcomment#SetOption("count", 7)
onoremap <Plug>TComment_7 :call tcomment#SetOption("count", 7)
vnoremap <Plug>TComment_<C-_>6 :call tcomment#SetOption("count", 6)
vnoremap <Plug>TComment_6 :call tcomment#SetOption("count", 6)
nnoremap <Plug>TComment_<C-_>6 :call tcomment#SetOption("count", 6)
onoremap <Plug>TComment_<C-_>6 :call tcomment#SetOption("count", 6)
nnoremap <Plug>TComment_6 :call tcomment#SetOption("count", 6)
onoremap <Plug>TComment_6 :call tcomment#SetOption("count", 6)
vnoremap <Plug>TComment_<C-_>5 :call tcomment#SetOption("count", 5)
vnoremap <Plug>TComment_5 :call tcomment#SetOption("count", 5)
nnoremap <Plug>TComment_<C-_>5 :call tcomment#SetOption("count", 5)
onoremap <Plug>TComment_<C-_>5 :call tcomment#SetOption("count", 5)
nnoremap <Plug>TComment_5 :call tcomment#SetOption("count", 5)
onoremap <Plug>TComment_5 :call tcomment#SetOption("count", 5)
vnoremap <Plug>TComment_<C-_>4 :call tcomment#SetOption("count", 4)
vnoremap <Plug>TComment_4 :call tcomment#SetOption("count", 4)
nnoremap <Plug>TComment_<C-_>4 :call tcomment#SetOption("count", 4)
onoremap <Plug>TComment_<C-_>4 :call tcomment#SetOption("count", 4)
nnoremap <Plug>TComment_4 :call tcomment#SetOption("count", 4)
onoremap <Plug>TComment_4 :call tcomment#SetOption("count", 4)
vnoremap <Plug>TComment_<C-_>3 :call tcomment#SetOption("count", 3)
vnoremap <Plug>TComment_3 :call tcomment#SetOption("count", 3)
nnoremap <Plug>TComment_<C-_>3 :call tcomment#SetOption("count", 3)
onoremap <Plug>TComment_<C-_>3 :call tcomment#SetOption("count", 3)
nnoremap <Plug>TComment_3 :call tcomment#SetOption("count", 3)
onoremap <Plug>TComment_3 :call tcomment#SetOption("count", 3)
vnoremap <Plug>TComment_<C-_>2 :call tcomment#SetOption("count", 2)
vnoremap <Plug>TComment_2 :call tcomment#SetOption("count", 2)
nnoremap <Plug>TComment_<C-_>2 :call tcomment#SetOption("count", 2)
onoremap <Plug>TComment_<C-_>2 :call tcomment#SetOption("count", 2)
nnoremap <Plug>TComment_2 :call tcomment#SetOption("count", 2)
onoremap <Plug>TComment_2 :call tcomment#SetOption("count", 2)
vnoremap <Plug>TComment_<C-_>1 :call tcomment#SetOption("count", 1)
vnoremap <Plug>TComment_1 :call tcomment#SetOption("count", 1)
nnoremap <Plug>TComment_<C-_>1 :call tcomment#SetOption("count", 1)
onoremap <Plug>TComment_<C-_>1 :call tcomment#SetOption("count", 1)
nnoremap <Plug>TComment_1 :call tcomment#SetOption("count", 1)
onoremap <Plug>TComment_1 :call tcomment#SetOption("count", 1)
nnoremap <Plug>TComment_gC :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_gCg@
nnoremap <Plug>TComment_gc :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_gcg@
xnoremap <Plug>TComment_gc :TCommentMaybeInline
nnoremap <Plug>TComment_gcb :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_gcbg@
nnoremap <Plug>TComment_gcc :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_gccg@$
noremap <Plug>TComment_ic :call tcomment#textobject#InlineComment()
xnoremap <Plug>TComment_Comment :if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | '<,'>TCommentMaybeInline!
nnoremap <Plug>TComment_Commentb :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_Commentbg@
nnoremap <Plug>TComment_Commentc :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_Commentcg@$
nnoremap <Plug>TComment_Commentl :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_Commentlg@$
nnoremap <Plug>TComment_Comment :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_Commentg@
xnoremap <Plug>TComment_Uncomment :if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | call tcomment#SetOption("mode_extra", "U") | '<,'>TCommentMaybeInline
nnoremap <Plug>TComment_Uncommentb :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_Uncommentbg@
nnoremap <Plug>TComment_Uncommentc :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_Uncommentcg@$
nnoremap <Plug>TComment_Uncomment :call tcomment#ResetOption() | if v:count > 0 | call tcomment#SetOption("count", v:count) | endif | let w:tcommentPos = getpos(".") |set opfunc=TCommentOpFunc_Uncommentg@
noremap <Plug>TComment_\_s :TCommentAs =&ft_
noremap <Plug>TComment_\_n :TCommentAs =&ft 
noremap <Plug>TComment_\_a :TCommentAs 
noremap <Plug>TComment_\_b :TCommentBlock
noremap <Plug>TComment_\_r :TCommentRight
xnoremap <Plug>TComment_\_i :TCommentInline
noremap <Plug>TComment_\_  :TComment 
noremap <Plug>TComment_\_p vip:TComment
xnoremap <Plug>TComment_\__ :TCommentMaybeInline
nnoremap <Plug>TComment_\__ :TComment
snoremap <Plug>TComment_\__ :TComment
onoremap <Plug>TComment_\__ :TComment
noremap <Plug>TComment_<C-_>ca :call tcomment#SetOption("as", input("Comment as: ", &filetype, "customlist,tcomment#complete#Complete"))
noremap <Plug>TComment_ca :call tcomment#SetOption("as", input("Comment as: ", &filetype, "customlist,tcomment#complete#Complete"))
noremap <Plug>TComment_<C-_>cc :call tcomment#SetOption("count", v:count1)
noremap <Plug>TComment_cc :call tcomment#SetOption("count", v:count1)
noremap <Plug>TComment_<C-_>s :TCommentAs =&ft_
noremap <Plug>TComment_s :TCommentAs =&ft_
noremap <Plug>TComment_<C-_>n :TCommentAs =&ft 
noremap <Plug>TComment_n :TCommentAs =&ft 
noremap <Plug>TComment_<C-_>a :TCommentAs 
noremap <Plug>TComment_a :TCommentAs 
noremap <Plug>TComment_<C-_>b :TCommentBlock
noremap <Plug>TComment_b :TCommentBlock
noremap <Plug>TComment_<C-_>i v:TCommentInline mode=I#
noremap <Plug>TComment_i v:TCommentInline mode=I#
noremap <Plug>TComment_<C-_>r :TCommentRight
noremap <Plug>TComment_r :TCommentRight
noremap <Plug>TComment_<C-_>  :TComment 
noremap <Plug>TComment_  :TComment 
noremap <Plug>TComment_<C-_>p m`vip:TComment``
noremap <Plug>TComment_p m`vip:TComment``
vnoremap <Plug>TComment_<C-_><C-_> :TCommentMaybeInline
vnoremap <Plug>TComment_ :TCommentMaybeInline
nnoremap <Plug>TComment_<C-_><C-_> :TComment
onoremap <Plug>TComment_<C-_><C-_> :TComment
nnoremap <Plug>TComment_ :TComment
onoremap <Plug>TComment_ :TComment
nmap <silent> <C-T> :vs|:b#
nmap <silent> <C-X> :wincmd x
nmap <silent> <S-Right> :wincmd l
nmap <silent> <S-Left> :wincmd h
nmap <silent> <S-Down> :wincmd j
nmap <silent> <S-Up> :wincmd k
map <C-M> :TagbarToggle
map <C-F> :NERDTreeFind
map <C-N> :NERDTreeToggle
imap 	 <Plug>SuperTabForward
imap <silent> 9 <Plug>TComment_9
imap <silent> 8 <Plug>TComment_8
imap <silent> 7 <Plug>TComment_7
imap <silent> 6 <Plug>TComment_6
imap <silent> 5 <Plug>TComment_5
imap <silent> 4 <Plug>TComment_4
imap <silent> 3 <Plug>TComment_3
imap <silent> 2 <Plug>TComment_2
imap <silent> 1 <Plug>TComment_1
imap <silent> s <Plug>TComment_s
imap <silent> n <Plug>TComment_n
imap <silent> a <Plug>TComment_a
imap <silent> b <Plug>TComment_b
imap <silent> i <Plug>TComment_i
imap <silent> r <Plug>TComment_r
imap <silent>   <Plug>TComment_ 
imap <silent> p <Plug>TComment_p
imap <silent>  <Plug>TComment_
let &cpo=s:cpo_save
unlet s:cpo_save
set background=dark
set backspace=indent,eol,start
set backupdir=~/vimswp//
set directory=~/vimswp//
set expandtab
set fileencodings=ucs-bom,utf-8,default,latin1
set helplang=en
set laststatus=2
set nomodeline
set printoptions=paper:a4
set ruler
set runtimepath=~/.vim,~/.vim/pack/vendor/start/Spacegray,~/.vim/bundle/Vundle.vim,~/.vim/bundle/nerdtree,~/.vim/bundle/tagbar,~/.vim/bundle/supertab,~/.vim/bundle/vim-dispatch,~/.vim/bundle/ctags,~/.vim/bundle/tcomment_vim,~/.vim/bundle/vmustache,~/.vim/bundle/vim-test,~/.vim/bundle/vim-jsbeautify,~/.vim/bundle/neomake,~/.vim/bundle/vim-pencil,~/.vim/bundle/vim-markdown,~/.vim/bundle/vim-flavored-markdown,~/.vim/bundle/LanguageTool,~/.vim/bundle/colorsbox,~/.vim/bundle/colour-schemes,~/.vim/bundle/Spacegray.vim,~/.vim/bundle/ale,~/.vim/bundle/vim-lastplace,/var/lib/vim/addons,/etc/vim,/usr/share/vim/vimfiles,/usr/share/vim/vim82,/usr/share/vim/vimfiles/after,/etc/vim/after,/var/lib/vim/addons/after,~/.vim/after,~/.vim/bundle/Vundle.vim,~/.vim/bundle/Vundle.vim/after,~/.vim/bundle/nerdtree/after,~/.vim/bundle/tagbar/after,~/.vim/bundle/supertab/after,~/.vim/bundle/vim-dispatch/after,~/.vim/bundle/ctags/after,~/.vim/bundle/tcomment_vim/after,~/.vim/bundle/vmustache/after,~/.vim/bundle/vim-test/after,~/.vim/bundle/vim-jsbeautify/after,~/.vim/bundle/neomake/after,~/.vim/bundle/vim-pencil/after,~/.vim/bundle/vim-markdown/after,~/.vim/bundle/vim-flavored-markdown/after,~/.vim/bundle/LanguageTool/after,~/.vim/bundle/colorsbox/after,~/.vim/bundle/colour-schemes/after,~/.vim/bundle/Spacegray.vim/after,~/.vim/bundle/ale/after,~/.vim/bundle/vim-lastplace/after
set shiftwidth=4
set smarttab
set statusline=%f(%l/%c)
set suffixes=.bak,~,.swp,.o,.info,.aux,.log,.dvi,.bbl,.blg,.brf,.cb,.ind,.idx,.ilg,.inx,.out,.toc
set tabstop=4
set viminfo='10,\"100,:20,%,n~/.viminfo
set wildignore=*.pyc
let s:so_save = &g:so | let s:siso_save = &g:siso | setg so=0 siso=0 | setl so=-1 siso=-1
let v:this_session=expand("<sfile>:p")
silent only
silent tabonly
cd ~/repos/mysql-test-app
if expand('%') == '' && !&modified && line('$') <= 1 && getline(1) == ''
  let s:wipebuf = bufnr('%')
endif
set shortmess=aoO
argglobal
%argdel
set stal=2
tabnew
tabrewind
edit src/charm.py
argglobal
balt .github/workflows/ci.yaml
setlocal keymap=
setlocal noarabic
setlocal autoindent
setlocal backupcopy=
setlocal balloonexpr=
setlocal nobinary
setlocal nobreakindent
setlocal breakindentopt=
setlocal bufhidden=
setlocal buflisted
setlocal buftype=
setlocal nocindent
setlocal cinkeys=0{,0},0),0],:,!^F,o,O,e
setlocal cinoptions=
setlocal cinwords=if,else,while,do,for,switch
setlocal colorcolumn=
setlocal comments=b:#,fb:-
setlocal commentstring=#\ %s
setlocal complete=.,w,b,u,t,i
setlocal concealcursor=
setlocal conceallevel=0
setlocal completefunc=
setlocal nocopyindent
setlocal cryptmethod=
setlocal nocursorbind
setlocal nocursorcolumn
set cursorline
setlocal cursorline
setlocal cursorlineopt=both
setlocal define=^\\s*\\(def\\|class\\)
setlocal dictionary=
setlocal nodiff
setlocal equalprg=
setlocal errorformat=
setlocal expandtab
if &filetype != 'python'
setlocal filetype=python
endif
setlocal fixendofline
setlocal foldcolumn=0
setlocal foldenable
setlocal foldexpr=0
setlocal foldignore=#
setlocal foldlevel=0
setlocal foldmarker={{{,}}}
setlocal foldmethod=manual
setlocal foldminlines=1
setlocal foldnestmax=20
setlocal foldtext=foldtext()
setlocal formatexpr=
setlocal formatoptions=tcq
setlocal formatlistpat=^\\s*\\d\\+[\\]:.)}\\t\ ]\\s*
setlocal formatprg=
setlocal grepprg=
setlocal iminsert=0
setlocal imsearch=-1
setlocal include=^\\s*\\(from\\|import\\)
setlocal includeexpr=substitute(substitute(substitute(v:fname,b:grandparent_match,b:grandparent_sub,''),b:parent_match,b:parent_sub,''),b:child_match,b:child_sub,'g')
setlocal indentexpr=GetPythonIndent(v:lnum)
setlocal indentkeys=0{,0},0),0],:,!^F,o,O,e,<:>,=elif,=except
setlocal noinfercase
setlocal iskeyword=@,48-57,_,192-255
setlocal keywordprg=python3\ -m\ pydoc
setlocal nolinebreak
setlocal nolisp
setlocal lispwords=
setlocal nolist
setlocal listchars=
setlocal makeencoding=
setlocal makeprg=
setlocal matchpairs=(:),{:},[:]
setlocal nomodeline
setlocal modifiable
setlocal nrformats=bin,octal,hex
set number
setlocal number
setlocal numberwidth=4
setlocal omnifunc=python3complete#Complete
setlocal path=
setlocal nopreserveindent
setlocal nopreviewwindow
setlocal quoteescape=\\
setlocal noreadonly
setlocal norelativenumber
setlocal norightleft
setlocal rightleftcmd=search
setlocal noscrollbind
setlocal scrolloff=-1
setlocal shiftwidth=4
setlocal noshortname
setlocal showbreak=
setlocal sidescrolloff=-1
setlocal signcolumn=auto
setlocal nosmartindent
setlocal softtabstop=4
setlocal nospell
setlocal spellcapcheck=[.?!]\\_[\\])'\"\	\ ]\\+
setlocal spellfile=
setlocal spelllang=en
setlocal spelloptions=
setlocal statusline=
setlocal suffixesadd=.py
setlocal swapfile
setlocal synmaxcol=3000
if &syntax != 'python'
setlocal syntax=python
endif
setlocal tabstop=4
setlocal tagcase=
setlocal tagfunc=
setlocal tags=
setlocal termwinkey=
setlocal termwinscroll=10000
setlocal termwinsize=
setlocal textwidth=0
setlocal thesaurus=
setlocal thesaurusfunc=
setlocal noundofile
setlocal undolevels=-123456
setlocal varsofttabstop=
setlocal vartabstop=
setlocal virtualedit=
setlocal wincolor=
setlocal nowinfixheight
setlocal nowinfixwidth
set nowrap
setlocal nowrap
setlocal wrapmargin=0
silent! normal! zE
let &fdl = &fdl
let s:l = 163 - ((54 * winheight(0) + 27) / 55)
if s:l < 1 | let s:l = 1 | endif
keepjumps exe s:l
normal! zt
keepjumps 163
normal! 014|
tabnext
edit lib/charms/data_platform_libs/v0/data_interfaces.py
argglobal
setlocal keymap=
setlocal noarabic
setlocal autoindent
setlocal backupcopy=
setlocal balloonexpr=
setlocal nobinary
setlocal nobreakindent
setlocal breakindentopt=
setlocal bufhidden=
setlocal buflisted
setlocal buftype=
setlocal nocindent
setlocal cinkeys=0{,0},0),0],:,!^F,o,O,e
setlocal cinoptions=
setlocal cinwords=if,else,while,do,for,switch
setlocal colorcolumn=
setlocal comments=b:#,fb:-
setlocal commentstring=#\ %s
setlocal complete=.,w,b,u,t,i
setlocal concealcursor=
setlocal conceallevel=0
setlocal completefunc=
setlocal nocopyindent
setlocal cryptmethod=
setlocal nocursorbind
setlocal nocursorcolumn
set cursorline
setlocal cursorline
setlocal cursorlineopt=both
setlocal define=^\\s*\\(def\\|class\\)
setlocal dictionary=
setlocal nodiff
setlocal equalprg=
setlocal errorformat=
setlocal expandtab
if &filetype != 'python'
setlocal filetype=python
endif
setlocal fixendofline
setlocal foldcolumn=0
setlocal foldenable
setlocal foldexpr=0
setlocal foldignore=#
setlocal foldlevel=0
setlocal foldmarker={{{,}}}
setlocal foldmethod=manual
setlocal foldminlines=1
setlocal foldnestmax=20
setlocal foldtext=foldtext()
setlocal formatexpr=
setlocal formatoptions=tcq
setlocal formatlistpat=^\\s*\\d\\+[\\]:.)}\\t\ ]\\s*
setlocal formatprg=
setlocal grepprg=
setlocal iminsert=0
setlocal imsearch=-1
setlocal include=^\\s*\\(from\\|import\\)
setlocal includeexpr=substitute(substitute(substitute(v:fname,b:grandparent_match,b:grandparent_sub,''),b:parent_match,b:parent_sub,''),b:child_match,b:child_sub,'g')
setlocal indentexpr=GetPythonIndent(v:lnum)
setlocal indentkeys=0{,0},0),0],:,!^F,o,O,e,<:>,=elif,=except
setlocal noinfercase
setlocal iskeyword=@,48-57,_,192-255
setlocal keywordprg=python3\ -m\ pydoc
setlocal nolinebreak
setlocal nolisp
setlocal lispwords=
setlocal nolist
setlocal listchars=
setlocal makeencoding=
setlocal makeprg=
setlocal matchpairs=(:),{:},[:]
setlocal nomodeline
setlocal modifiable
setlocal nrformats=bin,octal,hex
set number
setlocal number
setlocal numberwidth=4
setlocal omnifunc=python3complete#Complete
setlocal path=
setlocal nopreserveindent
setlocal nopreviewwindow
setlocal quoteescape=\\
setlocal noreadonly
setlocal norelativenumber
setlocal norightleft
setlocal rightleftcmd=search
setlocal noscrollbind
setlocal scrolloff=-1
setlocal shiftwidth=4
setlocal noshortname
setlocal showbreak=
setlocal sidescrolloff=-1
setlocal signcolumn=auto
setlocal nosmartindent
setlocal softtabstop=4
setlocal nospell
setlocal spellcapcheck=[.?!]\\_[\\])'\"\	\ ]\\+
setlocal spellfile=
setlocal spelllang=en
setlocal spelloptions=
setlocal statusline=
setlocal suffixesadd=.py
setlocal swapfile
setlocal synmaxcol=3000
if &syntax != 'python'
setlocal syntax=python
endif
setlocal tabstop=4
setlocal tagcase=
setlocal tagfunc=
setlocal tags=
setlocal termwinkey=
setlocal termwinscroll=10000
setlocal termwinsize=
setlocal textwidth=0
setlocal thesaurus=
setlocal thesaurusfunc=
setlocal noundofile
setlocal undolevels=-123456
setlocal varsofttabstop=
setlocal vartabstop=
setlocal virtualedit=
setlocal wincolor=
setlocal nowinfixheight
setlocal nowinfixwidth
set nowrap
setlocal nowrap
setlocal wrapmargin=0
silent! normal! zE
let &fdl = &fdl
let s:l = 726 - ((54 * winheight(0) + 27) / 55)
if s:l < 1 | let s:l = 1 | endif
keepjumps exe s:l
normal! zt
keepjumps 726
normal! 0
tabnext 2
set stal=1
badd +11 .github/workflows/ci.yaml
badd +1 ~/repos/mysql-k8s-operator/.git/rebase-merge/git-rebase-todo
badd +1 src/charm.py
badd +4 src/literals.py
badd +0 lib/charms/data_platform_libs/v0/data_interfaces.py
if exists('s:wipebuf') && len(win_findbuf(s:wipebuf)) == 0
  silent exe 'bwipe ' . s:wipebuf
endif
unlet! s:wipebuf
set winheight=1 winwidth=20 shortmess=filnxtToOS
let s:sx = expand("<sfile>:p:r")."x.vim"
if filereadable(s:sx)
  exe "source " . fnameescape(s:sx)
endif
let &g:so = s:so_save | let &g:siso = s:siso_save
doautoall SessionLoadPost
unlet SessionLoad
" vim: set ft=vim :
