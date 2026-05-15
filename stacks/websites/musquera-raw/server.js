const express = require('express');
const { Pool } = require('pg');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const cookieParser = require('cookie-parser');
const { SitemapStream, streamToPromise } = require('sitemap');
const { createGzip } = require('zlib');

const app = express();
const port = process.env.PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET || 'CHANGE_ME_JWT_SECRET';

// Database Configuration
const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

// Multer for Vector File Uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadDir = './public/uploads';
    if (!fs.existsSync(uploadDir)) {
      fs.mkdirSync(uploadDir, { recursive: true });
    }
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    cb(null, `${Date.now()}-${file.originalname}`);
  }
});
const upload = multer({ storage });

app.use(express.json());
app.use(cookieParser());
// Serve Static Assets (Public folder only for security)
app.use('/public', express.static(path.join(__dirname, 'public')));
app.use('/img', express.static(path.join(__dirname, 'img')));

// Serve React Admin App
app.use('/admin', express.static(path.join(__dirname, 'admin-react/dist')));
app.get('/admin/*', (req, res) => {
  res.sendFile(path.join(__dirname, 'admin-react/dist', 'index.html'));
});

// Serve Main Portal
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});
app.use(express.static(path.join(__dirname, ''))); // Fallback for root assets (style.css, app.js etc)

app.get('/sitemap.xml', async (req, res) => {
  res.header('Content-Type', 'application/xml');
  res.header('Content-Encoding', 'gzip');

  try {
    const smStream = new SitemapStream({ hostname: 'https://musquera-lab.labrazahome.es' });
    const pipeline = smStream.pipe(createGzip());

    // 1. Static Routes
    smStream.write({ url: '/', changefreq: 'daily', priority: 1.0 });
    smStream.write({ url: '/admin', changefreq: 'monthly', priority: 0.1 });

    // 2. Dynamic Routes (Inventory Categories if needed)
    // For now, we only have the main portal pages.
    
    smStream.end();
    streamToPromise(pipeline).then(sm => res.send(sm));
  } catch (e) {
    console.error(e);
    res.status(500).end();
  }
});

// --- DATABASE INITIALIZATION ---
const initDb = async (retries = 5, delay = 3000) => {
    while (retries > 0) {
        try {
            // 1. users table
            await pool.query(`
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role VARCHAR(20) CHECK (role IN ('admin', 'manager', 'operator')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            `);

            // 2. orders table
            await pool.query(`
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    tracking_id TEXT UNIQUE,
                    client_name VARCHAR(100) NOT NULL,
                    event_date DATE,
                    technique TEXT,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    total_price DECIMAL(10,2),
                    status VARCHAR(20) DEFAULT 'received',
                    priority_level BOOLEAN DEFAULT FALSE,
                    assigned_to INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            `);

            // 3. activity_log (Forensic Audit)
            await pool.query(`
                CREATE TABLE IF NOT EXISTS activity_log (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    username VARCHAR(50),
                    order_id INTEGER REFERENCES orders(id),
                    action VARCHAR(100),
                    details TEXT,
                    ip_address VARCHAR(45),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            `);

            // 4. files table
            await pool.query(`
                CREATE TABLE IF NOT EXISTS archivos (
                    id SERIAL PRIMARY KEY,
                    order_id INT REFERENCES orders(id) ON DELETE CASCADE,
                    ruta_archivo TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            `);

            // 5. inventory table [PHASE_5]
            await pool.query(`
                CREATE TABLE IF NOT EXISTS inventory (
                    id SERIAL PRIMARY KEY,
                    item_name VARCHAR(100) NOT NULL,
                    size VARCHAR(10) NOT NULL,
                    color VARCHAR(30) NOT NULL,
                    stock_level INTEGER DEFAULT 0,
                    min_threshold INTEGER DEFAULT 10,
                    supplier VARCHAR(100),
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            `);

            // Safe Schema Extensions
            await pool.query('ALTER TABLE orders ADD COLUMN IF NOT EXISTS shipping_address TEXT');
            await pool.query('ALTER TABLE orders ADD COLUMN IF NOT EXISTS transport_agency VARCHAR(50)');
            await pool.query('ALTER TABLE orders ADD COLUMN IF NOT EXISTS transport_tracking TEXT');
            await pool.query('ALTER TABLE orders ADD COLUMN IF NOT EXISTS client_signature TEXT');
            await pool.query('ALTER TABLE orders ADD COLUMN IF NOT EXISTS notes TEXT');
            await pool.query('ALTER TABLE orders ADD COLUMN IF NOT EXISTS client_email VARCHAR(255)');
            await pool.query('ALTER TABLE orders ADD COLUMN IF NOT EXISTS client_phone VARCHAR(50)');
            await pool.query('ALTER TABLE orders ADD COLUMN IF NOT EXISTS cost_price DECIMAL(10,2) DEFAULT 0');

            // Initial Provisioning (admin/Musquera123456)
            const salt = await bcrypt.genSalt(10);
            const hashedAdmin = await bcrypt.hash('Musquera123456', salt);
            await pool.query(`
                INSERT INTO users (username, password_hash, role)
                VALUES ('admin', $1, 'admin')
                ON CONFLICT (username) DO NOTHING
            `, [hashedAdmin]);

            console.log("PostgreSQL Phase 4 Schema Initialized.");
            return;
        } catch (err) {
            console.error(`DB Init Error:`, err.message);
            retries -= 1;
            await new Promise(res => setTimeout(res, delay));
        }
    }
};
initDb();

// ── SETUP & INITIALIZATION (ONE-TIME) ──
app.post('/api/setup/admin', express.json(), async (req, res) => {
  const { username, password } = req.body;
  if (!username || !password) return res.status(400).json({ success: false, error: 'Username and password required.' });
  
  try {
    const userCount = await pool.query('SELECT COUNT(*) FROM users');
    if (parseInt(userCount.rows[0].count) > 0) {
      return res.status(403).json({ success: false, error: 'Setup already completed. Access locked.' });
    }

    const hashedPassword = await bcrypt.hash(password, 10);
    const newUser = await pool.query(
      'INSERT INTO users (username, password_hash, role) VALUES ($1, $2, $3) RETURNING id, username, role',
      [username, hashedPassword, 'admin']
    );

    await logActivity(newUser.rows[0].id, newUser.rows[0].username, 'SYSTEM_INITIALIZED', 'SuperAdmin account created via /setup', null, req.ip);
    
    res.json({ success: true, message: 'SuperAdmin initialized successfully.' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ success: false, error: 'Database error during setup.' });
  }
});

// --- MIDDLEWARE ---

// Helper for Trazabilidad Forense
const logActivity = async (userId, username, action, details = null, orderId = null, ipAddress = null) => {
  try {
    await pool.query(
      'INSERT INTO activity_log (user_id, username, action, details, order_id, ip_address) VALUES ($1, $2, $3, $4, $5, $6)',
      [userId, username, action, details, orderId, ipAddress]
    );
  } catch (err) {
    console.error('[LOG_ERROR]', err.message);
  }
};

// ── AUTOMATED NOTIFICATIONS (n8n Webhook) ──
const getTrackingLink = (id) => {
  if (!id) return '#';
  if (/^[0-9]{14,20}$/.test(id)) return `https://www.correos.es/es/es/herramientas/localizador/envios/detalle?devolucion=false&reintento=0&numero=${id}`;
  if (/^[0-9]{10}$/.test(id)) return `https://www.dhl.com/es-es/home/tracking/tracking-express.html?submit=1&tracking-id=${id}`;
  if (/^[A-Z0-9]{12}$/.test(id)) return `https://www.seur.com/livetracking/pages/seguimiento-online-busqueda.do?idSeguimiento=${id}`;
  if (/^[0-9]{12}$/.test(id)) return `https://www.fedex.com/fedextrack/?tracknumbers=${id}`;
  return '#';
};

const triggerNotification = async (order) => {
  const webhookUrl = process.env.N8N_WEBHOOK_URL;
  if (!webhookUrl) {
    console.log('[NOTIFY_OFF] N8N_WEBHOOK_URL not set.');
    return;
  }

  const trackingLink = getTrackingLink(order.transport_tracking);
  const payload = {
    event: 'order_shipped',
    tracking_id: order.tracking_id,
    client_name: order.client_name,
    client_email: order.client_email,
    client_phone: order.client_phone,
    transport_tracking: order.transport_tracking,
    tracking_link: trackingLink,
    message: `📦 [ENVÍO_CONFIRMADO] Tu pedido para ${order.client_name} ha salido del Lab. Rastréalo aquí: ${trackingLink}`
  };

  try {
    await fetch(webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    console.log(`[NOTIFY_SENT] Order ${order.tracking_id} via n8n.`);
  } catch (err) {
    console.error('[NOTIFY_ERROR]', err.message);
  }
};

// Authenticate JWT
const authenticate = (req, res, next) => {
  const token = req.cookies.mrf_token || req.headers['authorization']?.split(' ')[1];
  if (!token) return res.status(401).json({ success: false, error: 'No autorizado' });

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch (err) {
    res.status(401).json({ success: false, error: 'Sesión expirada' });
  }
};

// Role Based Access Control
const checkRole = (rolesPermitidos) => {
  return (req, res, next) => {
    if (!req.user || !rolesPermitidos.includes(req.user.role)) {
      console.error(`[ACCESO_DENEGADO] Usuario: ${req.user?.username || 'Anónimo'} intentó entrar en ruta protegida.`);
      return res.status(403).json({ success: false, error: 'Nivel de acceso insuficiente' });
    }
    next();
  };
};

// --- API ROUTES ---

// Admin Login (Secure Auth)
app.post('/api/login', async (req, res) => {
  const { username, password } = req.body;
  try {
    const result = await pool.query('SELECT * FROM users WHERE username = $1', [username]);
    if (result.rows.length === 0) {
      return res.status(401).json({ success: false, error: 'Usuario no encontrado' });
    }

    const user = result.rows[0];
    const isMatch = await bcrypt.compare(password, user.password_hash);
    
    if (isMatch) {
      const token = jwt.sign(
        { id: user.id, username: user.username, role: user.role },
        JWT_SECRET,
        { expiresIn: '8h' }
      );

      console.log(`[AUTH] Login Success: ${username} (${user.role})`);
      
      // Set cookie for browser-side safety
      res.cookie('mrf_token', token, { httpOnly: true, secure: process.env.NODE_ENV === 'production' });
      
      res.json({ 
        success: true, 
        role: user.role,
        username: user.username,
        token: token 
      });
    } else {
      res.status(401).json({ success: false, error: 'Contraseña incorrecta' });
    }
  } catch (err) {
    res.status(500).json({ success: false, error: 'Error en el servidor' });
  }
});

app.get('/api/auth/session', authenticate, (req, res) => {
  res.json({
    success: true,
    user: {
      id: req.user.id,
      username: req.user.username,
      role: req.user.role
    }
  });
});

// Admin: Get System Logs
app.get('/api/admin/logs', authenticate, checkRole(['admin', 'manager']), async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 100');
    res.json({ success: true, logs: result.rows });
  } catch (err) {
    res.status(500).json({ success: false, error: 'Error fetching logs' });
  }
});

// Admin: Get All Orders (Orders Table)
app.get('/api/admin/orders', authenticate, checkRole(['admin', 'manager', 'operator']), async (req, res) => {
  try {
    let query = 'SELECT * FROM orders ORDER BY created_at DESC';
    const result = await pool.query(query);
    res.json({ success: true, orders: result.rows });
  } catch (err) {
    res.status(500).json({ success: false, error: 'Database error' });
  }
});

// Admin: Get Single Order Details + Images
app.get('/api/admin/orders/:tracking_id', authenticate, checkRole(['admin', 'manager', 'operator']), async (req, res) => {
  const { tracking_id } = req.params;
  try {
    const orderResult = await pool.query('SELECT * FROM orders WHERE tracking_id = $1', [tracking_id]);
    if (orderResult.rows.length === 0) return res.status(404).json({ success: false, error: 'Order not found' });
    const order = orderResult.rows[0];

    const filesResult = await pool.query('SELECT ruta_archivo, created_at FROM archivos WHERE order_id = $1', [order.id]);
    res.json({ success: true, order, files: filesResult.rows });
  } catch (err) {
    res.status(500).json({ success: false, error: 'Error fetching order details' });
  }
});

// Admin: Update Order Extra Details (Transport, Notes, Signature)
app.put('/api/admin/orders/:tracking_id/details', authenticate, checkRole(['admin', 'manager']), async (req, res) => {
  const { tracking_id } = req.params;
  const { 
    shipping_address, transport_agency, transport_tracking, 
    notes, client_signature, total_price 
  } = req.body;
  try {
    await pool.query(`
      UPDATE orders 
      SET shipping_address = $1, transport_agency = $2, transport_tracking = $3, notes = $4, client_signature = $5, total_price = $6
      WHERE tracking_id = $7
    `, [shipping_address, transport_agency, transport_tracking, notes, client_signature, total_price, tracking_id]);
    
    await logActivity(req.user.id, req.user.username, 'ORDER_DETAILS_UPDATED', `Pedido: ${tracking_id}`);
    
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ success: false, error: 'Error updating order details' });
  }
});

// Admin: Update Status (Modern status strings)
app.post('/api/admin/update-status', authenticate, checkRole(['admin', 'manager', 'operator']), async (req, res) => {
  const { tracking_id, status, transport_agency, transport_tracking, assigned_to } = req.body;
  
  // [PHASE_6] Mandatory Logistics Validation
  if (status === 'shipped') {
    if (!transport_agency || !transport_tracking) {
      return res.status(400).json({ 
        success: false, 
        error: 'GESTIÓN_LOGÍSTICA: Es obligatorio indicar el Transportista y el Nº de seguimiento para marcar como ENVIADO.' 
      });
    }
  }

  try {
    const updateResult = await pool.query(
      'UPDATE orders SET status = $2, transport_agency = COALESCE($3, transport_agency), transport_tracking = COALESCE($4, transport_tracking), assigned_to = COALESCE($5, assigned_to) WHERE tracking_id = $1 RETURNING *',
      [tracking_id, status, transport_agency, transport_tracking, assigned_to]
    );

    if (updateResult.rows.length === 0) {
      return res.status(404).json({ success: false, error: 'Pedido no encontrado.' });
    }

    const order = updateResult.rows[0];
    await logActivity(req.user.id, req.user.username, 'STATUS_UPDATED', `Pedido ${tracking_id} -> ${status.toUpperCase()}${transport_tracking ? ' (Tracking: ' + transport_tracking + ')' : ''}`);
    
    // Auto-Notify if status is SHIPPED
    if (status.toUpperCase() === 'SHIPPED' || status.toUpperCase() === 'ENVIADO') {
      await triggerNotification(order);
    }

    res.json({ success: true, order });
  } catch (err) {
    res.status(500).json({ success: false, error: 'Error updating status' });
  }
});

// ── BI & FORENSICS: Audit Logs ──
app.get('/api/admin/audit', authenticate, checkRole(['admin', 'manager']), async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT a.*, u.username as operator_name, o.tracking_id as order_ref 
      FROM activity_log a
      LEFT JOIN users u ON a.user_id = u.id
      LEFT JOIN orders o ON a.order_id = o.id
      ORDER BY a.created_at DESC LIMIT 100
    `);
    res.json(result.rows);
  } catch (err) {
    res.status(500).json({ success: false, error: 'Error fetching audit logs' });
  }
});

// ── BI & FORENSICS: Heatmap Data ──
app.get('/api/admin/analytics/heatmap', authenticate, checkRole(['admin', 'manager']), async (req, res) => {
  try {
    const result = await pool.query('SELECT shipping_address, client_name FROM orders WHERE shipping_address IS NOT NULL');
    
    // Simple geocoding simulation (Mock coords for demo)
    const points = result.rows.map(row => {
      // Logic would be: geocode(row.shipping_address)
      // For now, providing semi-random coords in Spain
      return {
        lat: 40.4168 + (Math.random() - 0.5) * 5, // Near Madrid
        lng: -3.7038 + (Math.random() - 0.5) * 5, 
        intensity: Math.random()
      };
    });

    res.json(points);
  } catch (err) {
    res.status(500).json({ success: false, error: 'Error fetching heatmap data' });
  }
});

// Admin: Export CSV (Accounting)
app.get('/api/admin/export-csv', authenticate, checkRole(['admin', 'manager']), async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM orders ORDER BY created_at DESC');
    const orders = result.rows;

    let csv = 'Tracking_ID,Client,Date,Technique,Status,Quantity,Price\n';
    orders.forEach(o => {
      const fecha = o.created_at ? o.created_at.toISOString().split('T')[0] : 'N/A';
      csv += `${o.tracking_id},"${o.client_name}",${fecha},"${o.technique}",${o.status},${o.quantity || 0},${o.total_price || 0}\n`;
    });

    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', 'attachment; filename=Musquera_Accounting.csv');
    res.status(200).send(csv);
  } catch (err) {
    res.status(500).json({ success: false, error: 'Error generating CSV' });
  }
});

// --- USER MANAGEMENT (SuperAdmin Only) ---
app.post('/api/admin/users', authenticate, checkRole(['admin']), async (req, res) => {
  const { username, password, role } = req.body;
  try {
    const salt = await bcrypt.genSalt(10);
    const hashedPassword = await bcrypt.hash(password, salt);
    await pool.query(
      'INSERT INTO users (username, password_hash, role) VALUES ($1, $2, $3)',
      [username, hashedPassword, role]
    );
    
    await logActivity(req.user.id, req.user.username, 'USER_CREATED', `Nuevo usuario: ${username} (${role})`);
    
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ success: false, error: 'Error creating user' });
  }
});

app.put('/api/admin/users/:id/password', authenticate, checkRole(['admin']), async (req, res) => {
  const { id } = req.params;
  const { newPassword } = req.body;
  if (!newPassword) return res.status(400).json({ success: false, error: 'Contraseña vacía' });
  
  try {
    const salt = await bcrypt.genSalt(10);
    const hashedPassword = await bcrypt.hash(newPassword, salt);
    await pool.query('UPDATE users SET password_hash = $1 WHERE id = $2', [hashedPassword, id]);
    
    await logActivity(req.user.id, req.user.username, 'PASSWORD_CHANGED', `Cambio clave usuario ID: ${id}`);
    
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ success: false, error: 'Error updating password' });
  }
});

app.get('/api/admin/users', authenticate, checkRole(['admin']), async (req, res) => {
  try {
    const result = await pool.query('SELECT id, username, role, created_at FROM users');
    res.json({ success: true, users: result.rows });
  } catch (err) {
    res.status(500).json({ success: false, error: 'Error listing users' });
  }
});

// ── INVENTORY MANAGEMENT [PHASE_5] ──
app.get('/api/admin/inventory', authenticate, checkRole(['admin', 'manager']), async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM inventory ORDER BY item_name ASC');
    res.json(result.rows);
  } catch (err) {
    res.status(500).json({ success: false, error: 'Error fetching inventory' });
  }
});

app.post('/api/admin/inventory', authenticate, checkRole(['admin', 'manager']), async (req, res) => {
  const { item_name, size, color, stock_level, min_threshold, supplier } = req.body;
  try {
    await pool.query(
      'INSERT INTO inventory (item_name, size, color, stock_level, min_threshold, supplier) VALUES ($1, $2, $3, $4, $5, $6)',
      [item_name, size, color, parseInt(stock_level) || 0, parseInt(min_threshold) || 10, supplier]
    );
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ success: false, error: 'Error creating inventory item' });
  }
});

app.put('/api/admin/inventory/:id', authenticate, checkRole(['admin', 'manager']), async (req, res) => {
  const { id } = req.params;
  const { stock_level, min_threshold } = req.body;
  try {
    await pool.query(
      'UPDATE inventory SET stock_level = $1, min_threshold = $2, last_updated = CURRENT_TIMESTAMP WHERE id = $3',
      [parseInt(stock_level), parseInt(min_threshold), id]
    );
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ success: false, error: 'Error updating stock' });
  }
});

// Customer: Track Status
app.get('/api/status/:id', async (req, res) => {
  const { id } = req.params;
  try {
    const result = await pool.query('SELECT status FROM orders WHERE tracking_id = $1', [id]);
    if (result.rows.length > 0) {
      res.json({ success: true, status: result.rows[0].status.toUpperCase() });
    } else {
      res.status(404).json({ success: false, error: "Order not found" });
    }
  } catch (err) {
    res.status(500).json({ success: false, error: "Database error" });
  }
});

// B2B Form Submission
app.post('/api/orders', upload.single('vectorFile'), async (req, res) => {
  const { clientName, eventDate, technique, quantity, notes, clientSignature } = req.body;
  const filePath = req.file ? req.file.path : null;

  try {
    const result = await pool.query(
      'INSERT INTO orders (client_name, event_date, technique, status, quantity, notes, client_signature) VALUES ($1, $2, $3, \'received\', $4, $5, $6) RETURNING id',
      [clientName, eventDate, technique, parseInt(quantity) || 1, notes, clientSignature]
    );
    const trackingId = `B2B-${result.rows[0].id}`;
    await pool.query('UPDATE orders SET tracking_id = $1 WHERE id = $2', [trackingId, result.rows[0].id]);
    
    if (filePath) {
      await pool.query('INSERT INTO archivos (order_id, ruta_archivo) VALUES ($1, $2)', [result.rows[0].id, filePath]);
    }
    res.status(201).json({ success: true, trackingId });
  } catch (err) {
    res.status(500).json({ success: false, error: "Error saving B2B order" });
  }
});

// Lab Order Submission
app.post('/api/lab-order', async (req, res) => {
  const { cliente, tecnica, total, trackingId, cantidad, notes, clientSignature } = req.body;
  try {
    await pool.query(
      'INSERT INTO orders (tracking_id, client_name, technique, total_price, status, quantity, notes, client_signature) VALUES ($1, $2, $3, $4, \'received\', $5, $6, $7)',
      [trackingId, cliente, tecnica, total, parseInt(cantidad) || 1, notes, clientSignature]
    );
    res.status(201).json({ success: true, orderId: trackingId });
  } catch (err) {
    res.status(500).json({ success: false, error: "Error saving lab order" });
  }
});

app.listen(port, () => {
  console.log(`MUSQUERA RAW FACTORY SERVER RUNNING ON PORT ${port}`);
});
