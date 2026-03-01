export function drawParticles(ctx, particlesRef) {
    particlesRef.current = particlesRef.current.filter(p => {
        p.x += p.vx;
        p.y += p.vy;
        p.life--;
        p.size *= 0.98;

        if (p.life <= 0) return false;

        ctx.fillStyle = p.color;
        ctx.fillRect(p.x, p.y, p.size, p.size);
        return true;
    });
}

export function addSteamParticle(x, y, particlesRef) {
    particlesRef.current.push({
        x: x,
        y: y,
        vx: (Math.random() - 0.5) * 0.5,
        vy: -0.5 - Math.random() * 0.5,
        life: 60,
        color: 'rgba(255,255,255,0.5)',
        size: 2
    });
}

export function addSparkleParticle(x, y, particlesRef, color = '#FFD700') {
    particlesRef.current.push({
        x: x,
        y: y,
        vx: (Math.random() - 0.5) * 2,
        vy: (Math.random() - 0.5) * 2,
        life: 30,
        color: color,
        size: 3
    });
}

export function drawGlow(ctx, px, py, color, radius = 20) {
    const gradient = ctx.createRadialGradient(px + 16, py + 16, 0, px + 16, py + 16, radius);
    gradient.addColorStop(0, color);
    gradient.addColorStop(1, 'transparent');
    ctx.fillStyle = gradient;
    ctx.fillRect(px - radius + 16, py - radius + 16, radius * 2, radius * 2);
}