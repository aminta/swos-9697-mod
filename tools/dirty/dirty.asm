; DIRTY.COM (4.0.6 harness, SWOSTEST_DIRTY): fill the memory DOS/4GW will hand to the game with a byte, as real
; hardware leaves it (DOSBox-X starts with zeroed RAM and hid uninitialised-buffer bugs: Davide's MiSTer, I8 03/11).
; Usage: DIRTY xx  (hex byte, default 5A). Free conventional memory above this program's 64 KB, then every free XMS
; block: allocated (largest first, until none left), filled by XMS moves from a 32 KB buffer, then all freed.
; Prints "DIRTY xx: conv nnnn para, xms nnnnn KB in n blocks".
bits 16
org 0x100
start:
    mov si, 0x81                    ; the fill byte from the command tail
    call hexarg
    mov [fill], al
    ; --- conventional: segments from cs+1000h up to the PSP's top-of-memory word
    mov ax, cs
    add ax, 0x1000
    mov bx, [2]                     ; (PSP:2: first segment after the program's block)
    xor dx, dx
.conv:
    cmp ax, bx
    jae .convdone
    mov es, ax
    xor di, di
    mov cx, 16
    mov al, [fill]
    rep stosb
    mov ax, es
    inc ax
    inc dx
    jmp .conv
.convdone:
    mov [convp], dx
    ; --- the 32 KB move source (in this segment: 0x8000..0xFFFF minus the stack's top 256 B: use 0x4000..0xBFFF)
    push cs
    pop es
    mov di, buf
    mov cx, 0x8000
    mov al, [fill]
    rep stosb
    ; --- XMS
    mov [mv_sseg], cs
    mov ax, 0x4300
    int 0x2f
    cmp al, 0x80
    jne .report
    mov ax, 0x4310
    int 0x2f
    mov [xms], bx
    mov [xms + 2], es
.alloc:
    cmp word [nh], 16
    jae .free
    mov ah, 0x08                    ; largest free block (KB) -> AX
    call far [xms]
    or ax, ax
    jz .free
    mov [blk], ax
    mov dx, ax
    mov ah, 0x09
    call far [xms]
    or ax, ax
    jz .free
    mov bx, [nh]
    shl bx, 1
    mov [hs + bx], dx
    inc word [nh]
    mov ax, [blk]
    add [kb], ax
    mov [pb_sh], dx                 ; (probe: the block's first 16 bytes -> probe, before the fill)
    mov word [pb_dseg], cs
    mov si, pb
    mov ah, 0x0b
    call far [xms]
    mov al, [probe]
    mov [first], al
    mov dx, [mv_dh]
    mov dx, [pb_sh]
    ; fill it: 32 KB moves, (blk * 1024) / 32768 = blk / 32 moves
    mov [mv_dh], dx
    mov word [mv_doff], 0
    mov word [mv_doff + 2], 0
    mov cx, [blk]
    shr cx, 5
.mv:
    jcxz .alloc
    push cx
    mov si, mv
    mov ah, 0x0b
    call far [xms]
    pop cx
    add word [mv_doff], 0x8000      ; (offset += 32768)
    adc word [mv_doff + 2], 0
    dec cx
    jmp .mv
.free:
    mov cx, [nh]
    xor bx, bx
.fr:
    jcxz .report
    mov dx, [hs + bx]
    push bx
    push cx
    mov ah, 0x0a
    call far [xms]
    pop cx
    pop bx
    add bx, 2
    dec cx
    jmp .fr
.report:
    mov dx, msg1
    call puts
    mov al, [fill]
    call puthex8
    mov dx, msg2
    call puts
    mov ax, [convp]
    call putdec
    mov dx, msg3
    call puts
    mov ax, [kb]
    call putdec
    mov dx, msg4
    call puts
    mov ax, [nh]
    call putdec
    mov dx, msg6
    call puts
    mov al, [first]
    call puthex8
    mov dx, msg5
    call puts
    mov ax, 0x4c00
    int 0x21

hexarg:                             ; first hex byte in the command tail -> AL (5A if none)
    mov cl, [0x80]
    xor ch, ch
    xor bx, bx
    xor dx, dx                      ; dl = digits seen
.n: jcxz .e
    lodsb
    dec cx
    call hexval
    jc .n
    shl bl, 4
    or bl, al
    inc dl
    cmp dl, 2
    jb .n
.e: mov al, bl
    or dl, dl
    jnz .r
    mov al, 0x5a
.r: ret
hexval:                             ; AL char -> AL 0..15, CF if not hex
    cmp al, '0'
    jb .no
    cmp al, '9'
    jbe .d
    or al, 0x20
    cmp al, 'a'
    jb .no
    cmp al, 'f'
    ja .no
    sub al, 'a' - 10
    clc
    ret
.d: sub al, '0'
    clc
    ret
.no: stc
    ret
puts:
    mov ah, 0x09
    int 0x21
    ret
puthex8:
    push ax
    shr al, 4
    call .dig
    pop ax
    and al, 15
.dig:
    add al, '0'
    cmp al, '9'
    jbe .p
    add al, 7
.p: mov dl, al
    mov ah, 0x02
    int 0x21
    ret
putdec:                             ; AX unsigned
    xor cx, cx
    mov bx, 10
.l: xor dx, dx
    div bx
    push dx
    inc cx
    or ax, ax
    jnz .l
.o: pop dx
    add dl, '0'
    mov ah, 0x02
    int 0x21
    loop .o
    ret

msg1 db 'DIRTY $'
msg2 db ': conv $'
msg3 db ' para, xms $'
msg4 db ' KB in $'
msg5 db 13, 10, '$'
msg6 db ' blocks, found $'
fill db 0x5a
convp dw 0
kb dw 0
nh dw 0
blk dw 0
xms dd 0
mv:                                 ; XMS move struct (fn 0Bh): length, src handle 0 = conventional seg:off, dst
mv_len  dd 0x8000
mv_sh   dw 0
mv_soff dw buf
mv_sseg dw 0
mv_dh   dw 0
mv_doff dd 0
hs times 16 dw 0
first db 0
pb:                                 ; probe move: 16 bytes from the block (offset 0) to probe
pb_len  dd 16
pb_sh   dw 0
pb_soff dd 0
pb_dh   dw 0
pb_doff dw probe
pb_dseg dw 0
probe times 16 db 0
align 16
buf:
